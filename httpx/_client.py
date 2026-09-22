import datetime
import enum
import logging
import ssl
import typing
import warnings
from contextlib import asynccontextmanager, contextmanager
from types import TracebackType

from .__version__ import __version__
from ._auth import Auth, BasicAuth, FunctionAuth
from ._config import (
    DEFAULT_LIMITS,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_TIMEOUT_CONFIG,
    Limits,
    Proxy,
    Timeout,
)
from ._decoders import SUPPORTED_DECODERS
from ._exceptions import (
    InvalidURL,
    RemoteProtocolError,
    TooManyRedirects,
    request_context,
)
from ._models import Cookies, Headers, Request, Response
from ._status_codes import codes
from ._transports.asgi import ASGITransport
from ._transports.base import AsyncBaseTransport, BaseTransport
from ._transports.default import AsyncHTTPTransport, HTTPTransport
from ._transports.wsgi import WSGITransport
from ._types import (
    AsyncByteStream,
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    ProxiesTypes,
    ProxyTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    SyncByteStream,
    TimeoutTypes,
    URLTypes,
)
from ._urls import URL, QueryParams
from ._utils import (
    Timer,
    URLPattern,
    get_environment_proxies,
    is_https_redirect,
    same_origin,
)

# The type annotation for @classmethod and context managers here follows PEP 484
# https://www.python.org/dev/peps/pep-0484/#annotating-instance-and-class-methods
T = typing.TypeVar("T", bound="Client")
U = typing.TypeVar("U", bound="AsyncClient")


class UseClientDefault:
    """
    For some parameters such as `auth=...` and `timeout=...` we need to be able
    to indicate the default "unset" state, in a way that is distinctly different
    to using `None`.

    The default "unset" state indicates that whatever default is set on the
    client should be used. This is different to setting `None`, which
    explicitly disables the parameter, possibly overriding a client default.

    For example we use `timeout=USE_CLIENT_DEFAULT` in the `request()` signature.
    Omitting the `timeout` parameter will send a request using whatever default
    timeout has been configured on the client. Including `timeout=None` will
    ensure no timeout is used.

    Note that user code shouldn't need to use the `USE_CLIENT_DEFAULT` constant,
    but it is used internally when a parameter is not included.
    """


USE_CLIENT_DEFAULT = UseClientDefault()


logger = logging.getLogger("httpx")

USER_AGENT = f"python-httpx/{__version__}"
ACCEPT_ENCODING = ", ".join(
    [key for key in SUPPORTED_DECODERS.keys() if key != "identity"]
)


class ClientState(enum.Enum):
    # UNOPENED:
    #   The client has been instantiated, but has not been used to send a request,
    #   or been opened by entering the context of a `with` block.
    UNOPENED = 1
    # OPENED:
    #   The client has either sent a request, or is within a `with` block.
    OPENED = 2
    # CLOSED:
    #   The client has either exited the `with` block, or `close()` has
    #   been called explicitly.
    CLOSED = 3


class BoundSyncStream(SyncByteStream):
    """
    A byte stream that is bound to a given response instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self, stream: SyncByteStream, response: Response, timer: Timer
    ) -> None:
        self._stream = stream
        self._response = response
        self._timer = timer

    def __iter__(self) -> typing.Iterator[bytes]:
        for chunk in self._stream:
            yield chunk

    def close(self) -> None:
        seconds = self._timer.sync_elapsed()
        self._response.elapsed = datetime.timedelta(seconds=seconds)
        self._stream.close()


class BoundAsyncStream(AsyncByteStream):
    """
    An async byte stream that is bound to a given response instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self, stream: AsyncByteStream, response: Response, timer: Timer
    ) -> None:
        self._stream = stream
        self._response = response
        self._timer = timer

    async def __aiter__(self) -> AsyncByteStream:
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        seconds = self._timer.async_elapsed()
        self._response.elapsed = datetime.timedelta(seconds=seconds)
        await self._stream.aclose()


class Client:
    """
    The `Client` is the primary entrypoint to the library. It is used to send
    HTTP requests, and to configure how those requests behave.

    Example...

    ```python
    >>> import httpx
    >>> client = httpx.Client()
    >>> client.get("https://example.org/")
    <Response [200 OK]>
    ```

    **Parameters:**

    * **http1_only** – Whether to only use HTTP/1.1. Defaults to `False`.
    * **http2** – Whether to use HTTP/2. Defaults to `True`.
    * **verify** – Whether to verify SSL certificates. Defaults to `True`.
    * **cert** – A tuple of cert (`*.pem`) and key (`*.key`) file paths.
    * **limits** – Configuration for HTTP connection limits.
    * **timeout** – Configuration for timeouts.
    * **follow_redirects** – Whether to automatically follow redirects. Defaults
      to `True`.
    * **proxies** – A dictionary of schemes or URLs to proxy URLs.
    * **transport** – A custom `httpcore.AsyncHTTPTransport` or `httpcore.HTTPTransport`
      implementation.
    * **http2_prior_knowledge** – Whether to assume the server speaks HTTP/2
      without HTTP/2 settings exchange. Defaults to `False`.
    """

    def __init__(
        self,
        *,
        http1_only: bool = False,
        http2: bool = True,
        verify: bool = True,
        cert: typing.Optional[typing.Tuple[bytes, bytes]] = None,
        limits: Limits = DEFAULT_LIMITS,
        timeout: Timeout = DEFAULT_TIMEOUT_CONFIG,
        follow_redirects: bool = True,
        proxies: typing.Optional[ProxiesTypes] = None,
        transport: typing.Optional[BaseTransport] = None,
        http2_prior_knowledge: bool = False,
    ) -> None:
        self._state = ClientState.UNOPENED
        self._limits = limits
        self._timeout = timeout
        self._follow_redirects = follow_redirects
        self._proxies = proxies
        self._transport = transport
        self._http2_prior_knowledge = http2_prior_knowledge

        if not http2:
            warnings.warn(
                "`http2` is deprecated and will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )

        self._auth: typing.Optional[Auth] = None
        self._headers: Headers = Headers()
        self._cookies: Cookies = Cookies()
        self._base_url: typing.Optional[URL] = None

        self._http1_only = http1_only
        self._verify = verify
        self._cert = cert

        self._default_headers: Headers = Headers()
        self._default_cookie_jar: Cookies = Cookies()

    @property
    def auth(self) -> typing.Optional[Auth]:
        """
        Authentication credentials.

        Example...

        ```python
        >>> client.auth = ("user", "password")
        >>> client.auth = BasicAuth("user", "password")
        >>> client.auth = FunctionAuth(lambda _: ("user", "password"))
        ```
        """
        return self._auth

    @auth.setter
    def auth(self, value: typing.Optional[Auth]) -> None:
        self._auth = value

    @property
    def headers(self) -> Headers:
        """
        Default HTTP headers.

        Example...

        ```python
        >>> client.headers["X-Foo"] = "Bar"
        >>> client.headers.update({"X-Bar": "Foo"})
        ```
        """
        return self._default_headers

    @headers.setter
    def headers(self, value: Headers) -> None:
        self._default_headers = Headers(value)

    @property
    def cookies(self) -> Cookies:
        """
        Default HTTP cookies.

        Example...

        ```python
        >>> client.cookies = {"session": "12345"}
        >>> client.cookies.update({"session": "67890"})
        ```
        """
        return self._default_cookie_jar

    @cookies.setter
    def cookies(self, value: Cookies) -> None:
        self._default_cookie_jar = Cookies(value)

    @property
    def base_url(self) -> typing.Optional[URL]:
        """
        A default base URL for all requests sent by this client.
        """
        return self._base_url

    @base_url.setter
    def base_url(self, value: typing.Optional[URL]) -> None:
        self._base_url = value

    @property
    def http1_only(self) -> bool:
        """
        Whether to use HTTP/1.1 only.
        """
        return self._http1_only

    @property
    def verify(self) -> bool:
        """
        Whether to verify SSL certificates.
        """
        return self._verify

    @verify.setter
    def verify(self, value: bool) -> None:
        self._verify = value

    @property
    def cert(self) -> typing.Optional[typing.Tuple[bytes, bytes]]:
        """
        A tuple of cert (`*.pem`) and key (`*.key`) file paths.
        """
        return self._cert

    @cert.setter
    def cert(self, value: typing.Optional[typing.Tuple[bytes, bytes]]) -> None:
        self._cert = value

    @property
    def limits(self) -> Limits:
        """
        Configuration for HTTP connection limits.
        """
        return self._limits

    @limits.setter
    def limits(self, value: Limits) -> None:
        self._limits = value

    @property
    def timeout(self) -> Timeout:
        """
        Configuration for timeouts.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: Timeout) -> None:
        self._timeout = value

    @property
    def follow_redirects(self) -> bool:
        """
        Whether to automatically follow redirects.
        """
        return self._follow_redirects

    @follow_redirects.setter
    def follow_redirects(self, value: bool) -> None:
        self._follow_redirects = value

    @property
    def proxies(self) -> typing.Optional[ProxiesTypes]:
        """
        A dictionary of schemes or URLs to proxy URLs.
        """
        return self._proxies

    @proxies.setter
    def proxies(self, value: typing.Optional[ProxiesTypes]) -> None:
        self._proxies = value

    @property
    def transport(self) -> typing.Optional[BaseTransport]:
        """
        A custom `httpcore.AsyncHTTPTransport` or `httpcore.HTTPTransport`
        implementation.
        """
        return self._transport

    @transport.setter
    def transport(self, value: typing.Optional[BaseTransport]) -> None:
        self._transport = value

    @property
    def http2_prior_knowledge(self) -> bool:
        """
        Whether to assume the server speaks HTTP/2 without HTTP/2
        settings exchange.
        """
        return self._http2_prior_knowledge

    @http2_prior_knowledge.setter
    def http2_prior_knowledge(self, value: bool) -> None:
        self._http2_prior_knowledge = value

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send an HTTP request.

        **Parameters:**

        * **method** – The request method, such as `"GET"`, `"POST"`, `"PUT"`, etc.
        * **url** – The URL to send the request to.
        * **content** – Raw bytes to send in the request body.
        * **data** – Form data to send in the request body.
        * **files** – Files to upload.
        * **json** – JSON data to send in the request body.
        * **params** – Query parameters to send with the request.
        * **headers** – Headers to send with the request.
        * **cookies** – Cookies to send with the request.
        * **auth** – Authentication credentials.
        * **follow_redirects** – Whether to automatically follow redirects.
        * **timeout** – Configuration for timeouts.
        * **extensions** – Additional request extensions.

        **Returns:**

        A `Response` instance.

        Example...

        ```python
        >>> import httpx
        >>> client = httpx.Client()
        >>> client.request("GET", "https://example.org/")
        <Response [200 OK]>
        ```
        """
        return self._request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def arequest(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send an HTTP request.

        **Parameters:**

        * **method** – The request method, such as `"GET"`, `"POST"`, `"PUT"`, etc.
        * **url** – The URL to send the request to.
        * **content** – Raw bytes to send in the request body.
        * **data** – Form data to send in the request body.
        * **files** – Files to upload.
        * **json** – JSON data to send in the request body.
        * **params** – Query parameters to send with the request.
        * **headers** – Headers to send with the request.
        * **cookies** – Cookies to send with the request.
        * **auth** – Authentication credentials.
        * **follow_redirects** – Whether to automatically follow redirects.
        * **timeout** – Configuration for timeouts.
        * **extensions** – Additional request extensions.

        **Returns:**

        A `Response` instance.

        Example...

        ```python
        >>> import httpx
        >>> async with httpx.AsyncClient() as client:
        ...     response = await client.arequest("GET", "https://example.org/")
        ...     response
        <Response [200 OK]>
        ```
        """
        return await self._arequest(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def _request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        return self._send(
            Request(
                method=method,
                url=url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
        )

    async def _arequest(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        return await self._asend(
            Request(
                method=method,
                url=url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
        )

    def _send(self, request: Request) -> Response:
        with request_context(request) as new_request:
            return self._send_handling_redirects(new_request)

    async def _asend(self, request: Request) -> Response:
        with request_context(request) as new_request:
            return await self._asend_handling_redirects(new_request)

    def _send_handling_redirects(
        self, request: Request
    ) -> typing.Union[Response, Response]:
        response = self._send_single_request(request)
        if self._follow_redirects:
            return self._handle_redirects(response)
        return response

    async def _asend_handling_redirects(
        self, request: Request
    ) -> typing.Union[Response, Response]:
        response = await self._asend_single_request(request)
        if self._follow_redirects:
            return await self._asend_handle_redirects(response)
        return response

    def _send_single_request(self, request: Request) -> Response:
        assert self._state == ClientState.OPENED, "Cannot send a request."
        assert self._transport is not None, "Cannot send a request."

        timer = Timer()
        with timer:
            response = self._transport.handle_request(request)
        return self._build_response(response, request, timer)

    async def _asend_single_request(self, request: Request) -> Response:
        assert self._state == ClientState.OPENED, "Cannot send a request."
        assert self._transport is not None, "Cannot send a request."

        timer = Timer()
        with timer:
            response = await self._transport.ahandle_request(request)
        return self._build_response(response, request, timer)

    def _handle_redirects(
        self, response: Response
    ) -> typing.Union[Response, Response]:
        assert isinstance(response.url, URL)

        redirect_location = response.headers.get("location", "")
        redirect_url = URL(redirect_location)

        if is_https_redirect(response.url, redirect_url):
            response = self._build_response(response, response.request, Timer())

        if not self._follow_redirects:
            return response

        if response.status_code in (
            codes.TEMPORARY_REDIRECT,
            codes.PERMANENT_REDIRECT,
        ):
            if redirect_url.is_absolute():
                request = self._build_redirect_request(response.request, redirect_url)
            else:
                request = self._build_redirect_request(
                    response.request, response.url.join(redirect_url)
                )
            return self._send_handling_redirects(request)

        if response.status_code == codes.FOUND:
            request = self._build_redirect_request(
                response.request, response.url.raw_path
            )
            return self._send_handling_redirects(request)

        return response

    async def _asend_handle_redirects(
        self, response: Response
    ) -> typing.Union[Response, Response]:
        assert isinstance(response.url, URL)

        redirect_location = response.headers.get("location", "")
        redirect_url = URL(redirect_location)

        if is_https_redirect(response.url, redirect_url):
            response = self._build_response(response, response.request, Timer())

        if not self._follow_redirects:
            return response

        if response.status_code in (
            codes.TEMPORARY_REDIRECT,
            codes.PERMANENT_REDIRECT,
        ):
            if redirect_url.is_absolute():
                request = self._build_redirect_request(response.request, redirect_url)
            else:
                request = self._build_redirect_request(
                    response.request, response.url.join(redirect_url)
                )
            return await self._asend_handling_redirects(request)

        if response.status_code == codes.FOUND:
            request = self._build_redirect_request(
                response.request, response.url.raw_path
            )
            return await self._asend_handling_redirects(request)

        return response

    def _build_redirect_request(
        self, request: Request, redirect_url: URL
    ) -> Request:
        new_request = request.copy()
        new_request.url = redirect_url
        new_request.headers["referer"] = request.url.raw
        return new_request

    def _build_response(
        self, response: Response, request: Request, timer: Timer
    ) -> Response:
        assert isinstance(response.url, URL)
        assert isinstance(response.headers, Headers)
        assert isinstance(response.content, (bytes, AsyncByteStream))

        if isinstance(response.content, AsyncByteStream):
            response.content = BoundAsyncStream(
                response.content, response, timer
            )  # type: ignore

        return Response(
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            request=request,
            extensions=response.extensions,
        )

    def _build_response_stream(
        self, stream: typing.Iterable[bytes]
    ) -> typing.Union[SyncByteStream, AsyncByteStream]:
        if isinstance(stream, AsyncByteStream):
            return BoundAsyncStream(stream, None, Timer())
        return BoundSyncStream(stream, None, Timer())

    def _build_response_from_stream(
        self,
        stream: typing.Iterable[bytes],
        request: Request,
        timer: Timer,
    ) -> Response:
        return Response(
            status_code=200,
            headers=Headers({"content-type": "application/octet-stream"}),
            content=self._build_response_stream(stream),
            request=request,
            extensions={},
        )

    def _build_request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Request:
        if isinstance(url, str):
            url = URL(url)

        if self._base_url is not None:
            if not url.is_absolute():
                url = self._base_url.join(url)
            else:
                # If the user specified an absolute URL, but also a base URL,
                # then we need to make sure that the absolute URL is relative
                # to the base URL.
                assert url.startswith(self._base_url.raw), (
                    "Cannot use an absolute URL when also specifying a base URL."
                )

        if params is not None:
            url = url.copy_with(query=QueryParams(url.raw_query, params))

        if headers is None:
            headers = Headers()
        else:
            headers = Headers(headers)

        if cookies is not None:
            headers.update(self._default_cookie_jar.update(cookies))

        if self._default_cookie_jar:
            headers.setdefault("cookie", "")

        if self._auth is not None:
            if isinstance(self._auth, Auth):
                auth = self._auth
            else:
                assert isinstance(self._auth, (tuple, list))
                auth = BasicAuth(*self._auth)
            headers.update(auth.get_auth_headers(url))

        if auth is not None:
            if isinstance(auth, Auth):
                auth = auth
            else:
                assert isinstance(auth, (tuple, list))
                auth = BasicAuth(*auth)
            headers.update(auth.get_auth_headers(url))

        if self._headers:
            headers.update(self._headers)

        if self._default_headers:
            headers.update(self._default_headers)

        if json is not None:
            headers.setdefault("content-type", "application/json")
            content = self._encode_json(json)

        if data is not None:
            if isinstance(data, str):
                headers.setdefault("content-type", "application/x-www-form-urlencoded")
                content = data.encode("utf-8")
            elif isinstance(data, (bytes, bytearray)):
                headers.setdefault("content-type", "application/octet-stream")
                content = data
            elif isinstance(data, dict):
                headers.setdefault("content-type", "application/x-www-form-urlencoded")
                qs = QueryParams()
                qs.update(data)
                qs.sort()
                qs_str = qs.build()
                content = qs_str.encode("utf-8")
            else:
                raise ValueError("Invalid data type.")

        if content is not None:
            headers.setdefault("content-length", str(len(content)))

        return Request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def _encode_json(self, json: typing.Any) -> bytes:
        import ujson

        return ujson.dumps(json).encode("utf-8")

    def _build_auth(self, auth: typing.Optional[AuthTypes]) -> typing.Optional[Auth]:
        if isinstance(auth, Auth):
            return auth
        elif isinstance(auth, (tuple, list)):
            return BasicAuth(*auth)
        elif auth is not None:
            return FunctionAuth(auth)
        return None

    def _build_timeout(
        self, timeout: TimeoutTypes
    ) -> typing.Union[Timeout, UseClientDefault]:
        if timeout is not None:
            return Timeout.from_float(timeout)
        return USE_CLIENT_DEFAULT

    def __enter__(self) -> "Client":
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    def __repr__(self) -> str:
        return f"<Client {self._state.name}>"

    def __del__(self) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the client.

        This will close the underlying HTTP connection pool, and cancel
        any pending requests.
        """
        if self._state != ClientState.CLOSED:
            self._state = ClientState.CLOSED

            if self._transport is not None:
                self._transport.close()

    def __enter__(self) -> "AsyncClient":
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    def __repr__(self) -> str:
        return f"<AsyncClient {self._state.name}>"

    def __del__(self) -> None:
        self.aclose()

    async def aclose(self) -> None:
        """
        Close the client.

        This will close the underlying HTTP connection pool, and cancel
        any pending requests.
        """
        if self._state != ClientState.CLOSED:
            self._state = ClientState.CLOSED

            if self._transport is not None:
                await self._transport.aclose()

    async def __aenter__(self: U) -> U:
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    async def __aenter__(self: U) -> U:
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    def __call__(
        self,
        method: str,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send an HTTP request.

        **Parameters:**

        * **method** – The request method, such as `"GET"`, `"POST"`, `"PUT"`, etc.
        * **url** – The URL to send the request to.
        * **content** – Raw bytes to send in the request body.
        * **data** – Form data to send in the request body.
        * **files** – Files to upload.
        * **json** – JSON data to send in the request body.
        * **params** – Query parameters to send with the request.
        * **headers** – Headers to send with the request.
        * **cookies** – Cookies to send with the request.
        * **auth** – Authentication credentials.
        * **follow_redirects** – Whether to automatically follow redirects.
        * **timeout** – Configuration for timeouts.
        * **extensions** – Additional request extensions.

        **Returns:**

        A `Response` instance.

        Example...

        ```python
        >>> import httpx
        >>> client = httpx.Client()
        >>> client("GET", "https://example.org/")
        <Response [200 OK]>
        ```
        """
        return self._request(
            method=method,
            url=url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def __aenter__(self: U) -> U:
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    async def __aenter__(self: U) -> U:
        assert self._state == ClientState.UNOPENED, "Cannot open a client instance."
        self._state = ClientState.OPENED
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

    def get(
        self,
        url: URLTypes,
        *,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return self._request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def aget(
        self,
        url: URLTypes,
        *,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return await self._arequest(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def options(
        self,
        url: URLTypes,
        *,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Response:
        """
        Send an `OPTIONS` request.

        **Parameters**: See `httpx.request`.
        """
        return self._request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    async def aoptions(
        self,
        url: URLTypes,
        *,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[