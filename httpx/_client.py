import datetime
import enum
import logging
import typing
import warnings
from contextlib import asynccontextmanager, contextmanager
from types import TraceBackType

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

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        seconds = self._timer.async_elapsed()
        self._response.elapsed = datetime.timedelta(seconds=seconds)
        await self._stream.aclose()


class Client:
    """
    The `Client` is the main entry point for sending HTTP requests.

    **Parameters:**

    - **base_url** – If provided, this URL will be prepended to all relative URLs
      passed to `request()`.

    - **transport** – The transport to use for sending requests. Defaults to
      `HTTPTransport`.

    - **limits** – Configuration for connection limits. Defaults to
      `DEFAULT_LIMITS`.

    - **timeout** – Configuration for request timeouts. Defaults to
      `DEFAULT_TIMEOUT_CONFIG`.

    - **follow_redirects** – Whether to automatically follow HTTP redirects.
      Defaults to `True`.

    - **http2** – Whether to use HTTP/2. Defaults to `True`.

    - **proxies** – Dictionary mapping protocol or protocol://host to the URL of
      the proxy.

    - **verify** – Whether to verify the server's TLS certificate. Defaults to
      `True`.

    - **cert** – The client certificate file path or keyring. Defaults to `None`.

    - **cookies** – A dictionary, key/value tuple, or `CookieJar` of cookies to
      send with each request. Defaults to `None`.

    - **headers** – A dictionary of headers to send with each request. Defaults
      to `None`.

    - **extensions** – A dictionary of extensions to enable on the client. The
      value for each key should be the initial value for the extension, which
      will be passed to the extension's `init()` method. Defaults to `None`.

    - **event_hooks** – A dictionary of event hooks to attach to the client.
      Defaults to `None`.

    - **dispatch** – A callable that accepts a `Request` instance and returns a
      `Response` instance. Defaults to `None`.
    """

    def __init__(
        self,
        *,
        base_url: typing.Optional[URLTypes] = None,
        transport: typing.Optional[BaseTransport] = None,
        limits: typing.Optional[Limits] = None,
        timeout: typing.Optional[Timeout] = None,
        follow_redirects: typing.Optional[bool] = None,
        http2: typing.Optional[bool] = None,
        proxies: typing.Optional[ProxiesTypes] = None,
        verify: typing.Optional[VerifyTypes] = None,
        cert: typing.Optional[CertTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        extensions: typing.Optional[RequestExtensions] = None,
        event_hooks: typing.Optional[RequestExtensions] = None,
        dispatch: typing.Optional[typing.Callable[[Request], Response]] = None,
    ) -> None:
        self._state = ClientState.UNOPENED
        self._base_url = URL(base_url) if base_url is not None else None
        self._transport = transport or HTTPTransport()
        self._limits = limits or DEFAULT_LIMITS
        self._timeout = timeout or DEFAULT_TIMEOUT_CONFIG
        self._follow_redirects = follow_redirects or True
        self._http2 = http2 or True
        self._proxies = proxies or {}
        self._verify = verify
        self._cert = cert
        self._cookies = Cookies(cookies)
        self._headers = Headers(headers)
        self._extensions = extensions or {}
        self._event_hooks = event_hooks or {}
        self._dispatch = dispatch

        self._mounts: typing.Dict[str, BaseTransport] = {}
        self._mount_pattern: typing.Dict[URLPattern, BaseTransport] = {}

        self._default_headers: typing.Dict[str, str] = {}
        self._default_verify: typing.Optional[VerifyTypes] = None
        self._default_http2: typing.Optional[bool] = None
        self._default_cookies: typing.Optional[CookieTypes] = None
        self._default_headers: typing.Optional[HeaderTypes] = None
        self._default_auth: typing.Optional[AuthTypes] = None
        self._default_timeout: typing.Optional[TimeoutTypes] = None
        self._default_proxies: typing.Optional[ProxiesTypes] = None
        self._default_cert: typing.Optional[CertTypes] = None
        self._default_event_hooks: typing.Optional[RequestExtensions] = None
        self._default_dispatch: typing.Optional[typing.Callable[[Request], Response]] = None

    def __repr__(self) -> str:
        return f"<Client[{self._transport!r}]>"

    @property
    def base_url(self) -> URL:
        """
        The base URL to use for relative URLs passed to `request()`.
        """
        if self._base_url is None:
            raise ValueError("No base URL has been set.")
        return self._base_url

    @base_url.setter
    def base_url(self, value: URLTypes) -> None:
        self._base_url = URL(value)

    @property
    def transport(self) -> BaseTransport:
        """
        The current transport.
        """
        return self._transport

    @property
    def limits(self) -> Limits:
        """
        Connection limits.
        """
        return self._limits

    @property
    def timeout(self) -> Timeout:
        """
        Request timeouts.
        """
        return self._timeout

    @property
    def follow_redirects(self) -> bool:
        """
        Whether to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def http2(self) -> bool:
        """
        Whether to use HTTP/2.
        """
        return self._http2

    @property
    def verify(self) -> typing.Optional[VerifyTypes]:
        """
        Whether to verify TLS certificates.
        """
        return self._verify

    @property
    def cert(self) -> typing.Optional[CertTypes]:
        """
        The TLS certificate to use.
        """
        return self._cert

    @property
    def cookies(self) -> Cookies:
        """
        A dictionary of cookies to send with each request.
        """
        return self._cookies

    @property
    def headers(self) -> Headers:
        """
        A dictionary of headers to send with each request.
        """
        return self._headers

    @property
    def extensions(self) -> RequestExtensions:
        """
        A dictionary of extensions to enable on the client.
        """
        return self._extensions

    @property
    def event_hooks(self) -> RequestExtensions:
        """
        A dictionary of event hooks to attach to the client.
        """
        return self._event_hooks

    @property
    def dispatch(self) -> typing.Optional[typing.Callable[[Request], Response]]:
        """
        A callable that accepts a `Request` instance and returns a `Response`
        instance.
        """
        return self._dispatch

    def __enter__(self) -> "Client":
        if self._state != ClientState.UNOPENED:
            msg = {
                ClientState.OPENED: "Cannot open a client instance more than once.",
                ClientState.CLOSED: (
                    "Cannot reopen a client instance, once it has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        self._state = ClientState.OPENED

        self._transport.__enter__()
        for proxy in self._mounts.values():
            if proxy is not None:
                proxy.__enter__()
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TraceBackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

        self._transport.__exit__(exc_type, exc_value, traceback)
        for proxy in self._mounts.values():
            if proxy is not None:
                proxy.__exit__(exc_type, exc_value, traceback)

    def __getstate__(self) -> typing.Dict[str, typing.Any]:
        state = {
            "_base_url": self._base_url,
            "_transport": self._transport,
            "_limits": self._limits,
            "_timeout": self._timeout,
            "_follow_redirects": self._follow_redirects,
            "_http2": self._http2,
            "_proxies": self._proxies,
            "_verify": self._verify,
            "_cert": self._cert,
            "_cookies": self._cookies,
            "_headers": self._headers,
            "_extensions": self._extensions,
            "_event_hooks": self._event_hooks,
            "_dispatch": self._dispatch,
            "_mounts": self._mounts,
            "_mount_pattern": self._mount_pattern,
            "_default_headers": self._default_headers,
            "_default_verify": self._default_verify,
            "_default_http2": self._default_http2,
            "_default_cookies": self._default_cookies,
            "_default_headers": self._default_headers,
            "_default_auth": self._default_auth,
            "_default_timeout": self._default_timeout,
            "_default_proxies": self._default_proxies,
            "_default_cert": self._default_cert,
            "_default_event_hooks": self._default_event_hooks,
            "_default_dispatch": self._default_dispatch,
        }
        return state

    def __setstate__(self, state: typing.Dict[str, typing.Any]) -> None:
        self._state = ClientState.UNOPENED

        self._base_url = state["_base_url"]
        self._transport = state["_transport"]
        self._limits = state["_limits"]
        self._timeout = state["_timeout"]
        self._follow_redirects = state["_follow_redirects"]
        self._http2 = state["_http2"]
        self._proxies = state["_proxies"]
        self._verify = state["_verify"]
        self._cert = state["_cert"]
        self._cookies = Cookies(state["_cookies"])
        self._headers = Headers(state["_headers"])
        self._extensions = state["_extensions"]
        self._event_hooks = state["_event_hooks"]
        self._dispatch = state["_dispatch"]
        self._mounts = state["_mounts"]
        self._mount_pattern = state["_mount_pattern"]
        self._default_headers = state["_default_headers"]
        self._default_verify = state["_default_verify"]
        self._default_http2 = state["_default_http2"]
        self._default_cookies = state["_default_cookies"]
        self._default_headers = state["_default_headers"]
        self._default_auth = state["_default_auth"]
        self._default_timeout = state["_default_timeout"]
        self._default_proxies = state["_default_proxies"]
        self._default_cert = state["_default_cert"]
        self._default_event_hooks = state["_default_event_hooks"]
        self._default_dispatch = state["_default_dispatch"]

    def __getattr__(self, name: str) -> typing.Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(
                f"Unknown attribute '{name}'. Available attributes are "
                f"{'.'.join(dir(self))}."
            )

        if name in self._extensions:
            return self._extensions[name]

        if name in self._event_hooks:
            return self._event_hooks[name]

        raise AttributeError(
            f"Unknown attribute '{name}'. Available attributes are "
            f"{'.'.join(dir(self))}."
        )

    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(
                f"Unknown attribute '{name}'. Available attributes are "
                f"{'.'.join(dir(self))}."
            )

        if name in self._extensions:
            self._extensions[name] = value
            return

        if name in self._event_hooks:
            self._event_hooks[name] = value
            return

        setattr(self, name, value)

    @property
    def default_headers(self) -> Headers:
        """
        Default headers to send with each request.
        """
        return Headers(headers=self._default_headers, encoding="ascii")

    @default_headers.setter
    def default_headers(self, value: HeaderTypes) -> None:
        self._default_headers = Headers(headers=value, encoding="ascii")

    @property
    def default_verify(self) -> typing.Optional[VerifyTypes]:
        """
        Default value for whether to verify TLS certificates.
        """
        return self._default_verify

    @default_verify.setter
    def default_verify(self, value: typing.Optional[VerifyTypes]) -> None:
        self._default_verify = value

    @property
    def default_http2(self) -> typing.Optional[bool]:
        """
        Default value for whether to use HTTP/2.
        """
        return self._default_http2

    @default_http2.setter
    def default_http2(self, value: typing.Optional[bool]) -> None:
        self._default_http2 = value

    @property
    def default_cookies(self) -> Cookies:
        """
        Default cookies to send with each request.
        """
        return Cookies(cookies=self._default_cookies)

    @default_cookies.setter
    def default_cookies(self, value: typing.Optional[CookieTypes]) -> None:
        self._default_cookies = Cookies(cookies=value)

    @property
    def default_headers(self) -> Headers:
        """
        Default headers to send with each request.
        """
        return Headers(headers=self._default_headers, encoding="ascii")

    @default_headers.setter
    def default_headers(self, value: HeaderTypes) -> None:
        self._default_headers = Headers(headers=value, encoding="ascii")

    @property
    def default_auth(self) -> typing.Optional[AuthTypes]:
        """
        Default authentication to use for each request.
        """
        return self._default_auth

    @default_auth.setter
    def default_auth(self, value: typing.Optional[AuthTypes]) -> None:
        self._default_auth = value

    @property
    def default_timeout(self) -> typing.Optional[TimeoutTypes]:
        """
        Default timeout for each request.
        """
        return self._default_timeout

    @default_timeout.setter
    def default_timeout(self, value: typing.Optional[TimeoutTypes]) -> None:
        self._default_timeout = value

    @property
    def default_proxies(self) -> typing.Optional[ProxiesTypes]:
        """
        Default proxies to use for each request.
        """
        return self._default_proxies

    @default_proxies.setter
    def default_proxies(self, value: typing.Optional[ProxiesTypes]) -> None:
        self._default_proxies = value

    @property
    def default_cert(self) -> typing.Optional[CertTypes]:
        """
        Default TLS certificate to use for each request.
        """
        return self._default_cert

    @default_cert.setter
    def default_cert(self, value: typing.Optional[CertTypes]) -> None:
        self._default_cert = value

    @property
    def default_event_hooks(self) -> RequestExtensions:
        """
        Default event hooks to attach to each request.
        """
        return self._default_event_hooks or {}

    @default_event_hooks.setter
    def default_event_hooks(self, value: typing.Optional[RequestExtensions]) -> None:
        self._default_event_hooks = Headers(headers=value, encoding="ascii")

    @property
    def default_dispatch(self) -> typing.Optional[typing.Callable[[Request], Response]]:
        """
        Default dispatch function to use for each request.
        """
        return self._default_dispatch

    @default_dispatch.setter
    def default_dispatch(
        self, value: typing.Optional[typing.Callable[[Request], Response]]
    ) -> None:
        self._default_dispatch = value

    def get(self, url: URLTypes, **kwargs: typing.Any) -> Response:
        """
        Send a `GET` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request("GET", url, **kwargs)

    def options(
        self,
        url: URLTypes,
        *,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
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
        return self.request(
            "OPTIONS",
            url,
            content=content,
            data=data,
            files=files,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def head(
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
        Send a `HEAD` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

    def post(
        self,
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
        Send a `POST` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "POST",
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

    def put(
        self,
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
        Send a `PUT` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PUT",
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

    def patch(
        self,
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
        Send a `PATCH` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "PATCH",
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

    def delete(
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
        Send a `DELETE` request.

        **Parameters**: See `httpx.request`.
        """
        return self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
        )

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

        **Parameters**:

        - **method** – The HTTP method to use for the request.

        - **url** – The URL to send the request to.

        - **content** – Raw bytes to send in the request body.

        - **data** – Form-encodable data to send in the request body.

        - **files** – A dictionary of `file` objects to send in the request
          body.

        - **json** – JSON-encodable data to send in the request body.

        - **params** – Query parameters to send with the request.

        - **headers** – Headers to send with the request.

        - **cookies** – Cookies to send with the request.

        - **auth** – Authentication to use for the request.

        - **follow_redirects** – Whether to automatically follow HTTP redirects.

        - **timeout** – The timeout to use for the request.

        - **extensions** – A dictionary of extensions to enable on the request.
        """
        if self._state != ClientState.OPENED:
            msg = {
                ClientState.UNOPENED: "Cannot send a request on an unopened client.",
                ClientState.CLOSED: "Cannot send a request on a closed client.",
            }[self._state]
            raise RuntimeError(msg)

        request = self._prepare_request(
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
            extensions=extensions,
        )

        response = self._send_request(request)

        return response

    def _prepare_request(
        self,
        *,
        method: str,
        url: URLTypes,
        content: typing.Optional[RequestContent] = None,
        data: typing.Optional[RequestData] = None,
        files: typing.Optional[RequestFiles] = None,
        json: typing.Optional[typing.Any] = None,
        params: typing.Optional[QueryParamTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        auth: typing.Union[AuthTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> Request:
        """
        Prepare a `Request` instance for sending.
        """
        # Prepare the URL.
        url = URL(url, base_url=self._base_url)

        # Prepare the headers.
        headers = Headers(headers=headers, encoding="ascii")

        # Prepare the cookies.
        cookies = Cookies(cookies)

        # Prepare the auth.
        if auth is USE_CLIENT_DEFAULT:
            auth = self._default_auth

        if auth is not None:
            if isinstance(auth, FunctionAuth):
                auth = auth.func()
            elif isinstance(auth, BasicAuth):
                auth = auth.auth
            elif isinstance(auth, Auth):
                auth = auth.build()

        # Prepare the timeout.
        if timeout is USE_CLIENT_DEFAULT:
            timeout = self._default_timeout

        if timeout is not None:
            if isinstance(timeout, Timeout):
                timeout = Timeout.from_float(timeout.total)
            elif isinstance(timeout, float):
                timeout = Timeout.from_float(timeout)
            elif isinstance(timeout, int):
                timeout = Timeout.from_float(timeout)

        # Prepare the extensions.
        if extensions is None:
            extensions = {}
        elif isinstance(extensions, RequestExtensions):
            extensions = extensions.copy()
        else:
            extensions = extensions.copy()

        # Prepare the request.
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
            extensions=extensions,
        )

        # Prepare the default headers.
        if self._default_headers:
            request.headers.update(self._default_headers)

        # Prepare the default cookies.
        if self._default_cookies:
            request.cookies.update(self._default_cookies)

        # Prepare the default auth.
        if self._default_auth:
            request.auth = self._default_auth

        # Prepare the default timeout.
        if self._default_timeout:
            request.timeout = self._default_timeout

        # Prepare the default extensions.
        if self._default_extensions:
            request.extensions.update(self._default_extensions)

        # Prepare the default verify.
        if self._default_verify is not None:
            request.extensions["verify"] = self._default_verify

        # Prepare the default http2.
        if self._default_http2 is not None:
            request.extensions["http2"] = self._default_http2

        # Prepare the default proxies.
        if self._default_proxies is not None:
            request.extensions["proxies"] = self._default_proxies

        # Prepare the default cert.
        if self._default_cert is not None:
            request.extensions["cert"] = self._default_cert

        # Prepare the default event hooks.
        if self._default_event_hooks:
            request.event_hooks.update(self._default_event_hooks)

        # Prepare the default dispatch.
        if self._default_dispatch is not None:
            request.dispatch = self._default_dispatch

        # Prepare the event hooks.
        event_hooks = self._prepare_event_hooks(request)

        # Prepare the dispatch.
        dispatch = self._prepare_dispatch(request)

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch=dispatch,
        )

        # Prepare the request.
        request = self._prepare_request(
            request=request,
            event_hooks=event_hooks,
            dispatch