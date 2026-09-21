import datetime
import enum
import logging
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
    CertTypes,
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
    VerifyTypes,
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

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        seconds = self._timer.async_elapsed()
        self._response.elapsed = datetime.timedelta(seconds=seconds)
        await self._stream.aclose()


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


class Client:
    """
    A client for sending HTTP requests.
    """

    def __init__(
        self,
        *,
        base_url: typing.Optional[URLTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        params: typing.Optional[QueryParamTypes] = None,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        max_redirects: typing.Optional[int] = DEFAULT_MAX_REDIRECTS,
        verify: typing.Union[VerifyTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        cert: typing.Union[CertTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        proxies: typing.Union[ProxiesTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        http1: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        http2: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        limits: typing.Union[Limits, UseClientDefault] = USE_CLIENT_DEFAULT,
        follow_all_redirects: typing.Optional[bool] = None,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> None:
        """
        **Parameters:**

        `base_url`:
            If provided, this URL will be added to the beginning of any relative URLs
            used when sending requests.

        `headers`:
            Default HTTP headers to include in all requests.

        `cookies`:
            Default HTTP cookies to include in all requests.

        `auth`:
            Default authentication credentials to include in all requests.

        `params`:
            Default query parameters to include in all requests.

        `timeout`:
            Default timeout, in seconds.

        `follow_redirects`:
            Whether to automatically follow HTTP redirects.

        `max_redirects`:
            The maximum number of redirects to follow.

        `verify`:
            Whether to verify SSL certificates.

        `cert`:
            Client-side SSL certificate.

        `proxies`:
            HTTP/HTTPS proxies to use.

        `http1`:
            Whether to enable HTTP/1.1.

        `http2`:
            Whether to enable HTTP/2.

        `limits`:
            Connection limits.

        `follow_all_redirects`:
            Whether to automatically follow HTTP redirects. Deprecated in
            favour of `follow_redirects`.

        `extensions`:
            Default extensions to include in all requests.
        """
        self._state = ClientState.UNOPENED

        if follow_all_redirects is not None:
            warnings.warn(
                "`follow_all_redirects` is deprecated, use `follow_redirects`",
                DeprecationWarning,
                stacklevel=2,
            )
            follow_redirects = bool(follow_all_redirects)

        self._base_url = URL(base_url) if base_url is not None else None
        self._headers = Headers(headers)
        self._cookies = Cookies(cookies)
        self._auth = Auth(auth)
        self._params = QueryParams(params)
        self._timeout = Timeout(timeout)
        self._follow_redirects = bool(follow_redirects)
        self._max_redirects = max_redirects
        self._verify = verify
        self._cert = cert
        self._proxies = Proxies(proxies)
        self._http1 = bool(http1)
        self._http2 = bool(http2)
        self._limits = Limits(limits)
        self._extensions = RequestExtensions(extensions)

        self._transport: BaseTransport = self._get_transport()

    def _get_transport(self) -> BaseTransport:
        return HTTPTransport(
            limits=self._limits,
            http1=self._http1,
            http2=self._http2,
            verify=self._verify,
            cert=self._cert,
            proxies=self._proxies,
            extensions=self._extensions,
        )

    @property
    def base_url(self) -> typing.Optional[URL]:
        """
        The base URL for all requests.
        """
        return self._base_url

    @property
    def headers(self) -> Headers:
        """
        Default HTTP headers to include in all requests.
        """
        return self._headers

    @headers.setter
    def headers(self, value: HeaderTypes) -> None:
        self._headers = Headers(value)

    @property
    def cookies(self) -> Cookies:
        """
        Default HTTP cookies to include in all requests.
        """
        return self._cookies

    @cookies.setter
    def cookies(self, value: CookieTypes) -> None:
        self._cookies = Cookies(value)

    @property
    def auth(self) -> Auth:
        """
        Default authentication credentials to include in all requests.
        """
        return self._auth

    @auth.setter
    def auth(self, value: AuthTypes) -> None:
        self._auth = Auth(value)

    @property
    def params(self) -> QueryParams:
        """
        Default query parameters to include in all requests.
        """
        return self._params

    @params.setter
    def params(self, value: QueryParamTypes) -> None:
        self._params = QueryParams(value)

    @property
    def timeout(self) -> Timeout:
        """
        Default timeout, in seconds.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: TimeoutTypes) -> None:
        self._timeout = Timeout(value)

    @property
    def follow_redirects(self) -> bool:
        """
        Whether to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @follow_redirects.setter
    def follow_redirects(self, value: bool) -> None:
        self._follow_redirects = bool(value)

    @property
    def max_redirects(self) -> typing.Optional[int]:
        """
        The maximum number of redirects to follow.
        """
        return self._max_redirects

    @max_redirects.setter
    def max_redirects(self, value: typing.Optional[int]) -> None:
        self._max_redirects = value

    @property
    def verify(self) -> VerifyTypes:
        """
        Whether to verify SSL certificates.
        """
        return self._verify

    @verify.setter
    def verify(self, value: VerifyTypes) -> None:
        self._verify = value

    @property
    def cert(self) -> CertTypes:
        """
        Client-side SSL certificate.
        """
        return self._cert

    @cert.setter
    def cert(self, value: CertTypes) -> None:
        self._cert = value

    @property
    def proxies(self) -> ProxiesTypes:
        """
        HTTP/HTTPS proxies to use.
        """
        return self._proxies

    @proxies.setter
    def proxies(self, value: ProxiesTypes) -> None:
        self._proxies = Proxies(value)

    @property
    def http1(self) -> bool:
        """
        Whether to enable HTTP/1.1.
        """
        return self._http1

    @http1.setter
    def http1(self, value: bool) -> None:
        self._http1 = bool(value)

    @property
    def http2(self) -> bool:
        """
        Whether to enable HTTP/2.
        """
        return self._http2

    @http2.setter
    def http2(self, value: bool) -> None:
        self._http2 = bool(value)

    @property
    def limits(self) -> Limits:
        """
        Connection limits.
        """
        return self._limits

    @limits.setter
    def limits(self, value: Limits) -> None:
        self._limits = Limits(value)

    @property
    def extensions(self) -> RequestExtensions:
        """
        Default extensions to include in all requests.
        """
        return self._extensions

    @extensions.setter
    def extensions(self, value: RequestExtensions) -> None:
        self._extensions = RequestExtensions(value)

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

        `method`:
            The request method, such as `GET`, `POST`, `PUT`, etc.

        `url`:
            The URL to send the request to.

        `content`:
            Raw bytes to send in the body of the request.

        `data`:
            Form data to send in the body of the request.

        `files`:
            Files to send in the body of the request.

        `json`:
            JSON data to send in the body of the request.

        `params`:
            Query parameters to include in the request.

        `headers`:
            Additional HTTP headers to include in the request.

        `cookies`:
            Additional HTTP cookies to include in the request.

        `auth`:
            Authentication credentials to include in the request.

        `follow_redirects`:
            Whether to automatically follow HTTP redirects.

        `timeout`:
            Request timeout, in seconds.

        `extensions`:
            Additional extensions to include in the request.
        """
        if self._state != ClientState.OPENED:
            msg = {
                ClientState.UNOPENED: "Cannot send a request until the client is opened.",
                ClientState.CLOSED: (
                    "Cannot send a request, once the client has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        request = self._prepare_request(
            method,
            url,
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

        timer = Timer()
        timer.start()
        response = self._send_request(request)
        timer.stop()

        response.elapsed = timer.elapsed
        return response

    def _prepare_request(
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
        if self._state != ClientState.OPENED:
            msg = {
                ClientState.UNOPENED: "Cannot prepare a request until the client is opened.",
                ClientState.CLOSED: (
                    "Cannot prepare a request, once the client has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        if isinstance(auth, UseClientDefault):
            auth = self._auth
        if isinstance(headers, UseClientDefault):
            headers = self._headers
        if isinstance(cookies, UseClientDefault):
            cookies = self._cookies
        if isinstance(params, UseClientDefault):
            params = self._params
        if isinstance(timeout, UseClientDefault):
            timeout = self._timeout
        if isinstance(follow_redirects, UseClientDefault):
            follow_redirects = self._follow_redirects

        url = URL(url, base_url=self._base_url)
        params = QueryParams(params, url=url)
        headers = Headers(headers, encoding=headers.encoding)
        cookies = Cookies(cookies, headers=headers, jar=self._cookies.jar)
        auth = Auth(auth, headers=headers, cookies=cookies)

        request = Request(
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
            timeout=timeout,
            extensions