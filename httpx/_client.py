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

    async def __aiter__(self) -> AsyncByteStream:
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
    A client for sending HTTP requests.

    **Parameters**:

    * **base_url** – The base URL to use for all requests sent by this client.
    * **auth** – Default authentication configuration to use for all requests.
    * **cookies** – Default cookies to use for all requests.
    * **headers** – Default headers to use for all requests.
    * **params** – Default query parameters to use for all requests.
    * **verify** – Enable TLS certificate verification.
    * **cert** – Client certificate to use for TLS authentication.
    * **proxies** – Default proxies to use for all requests.
    * **timeout** – Default timeout for requests.
    * **limits** – Default limits to use for requests.
    * **extensions** – Default extensions to use for all requests.
    """

    def __init__(
        self,
        *,
        base_url: typing.Optional[URLTypes] = None,
        auth: typing.Optional[AuthTypes] = None,
        cookies: typing.Optional[CookieTypes] = None,
        headers: typing.Optional[HeaderTypes] = None,
        params: typing.Optional[QueryParamTypes] = None,
        verify: typing.Union[bool, str, VerifyTypes] = True,
        cert: typing.Optional[CertTypes] = None,
        proxies: typing.Optional[ProxiesTypes] = None,
        timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
        limits: typing.Optional[Limits] = None,
        extensions: typing.Optional[RequestExtensions] = None,
    ) -> None:
        self._state = ClientState.UNOPENED

        self._base_url = URL(base_url) if base_url is not None else None
        self._auth = Auth(auth) if auth is not None else None
        self._cookies = Cookies(cookies)
        self._headers = Headers(headers)
        self._params = QueryParams(params)
        self._verify = verify
        self._cert = cert
        self._proxies = proxies
        self._timeout = DEFAULT_TIMEOUT_CONFIG if timeout is USE_CLIENT_DEFAULT else timeout
        self._limits = DEFAULT_LIMITS if limits is None else limits
        self._extensions = extensions

        self._transport: BaseTransport
        self._mounts: typing.Dict[str, BaseTransport] = {}

    @property
    def base_url(self) -> URL:
        """
        The base URL to use for all requests.
        """
        return self._base_url

    @base_url.setter
    def base_url(self, value: URLTypes) -> None:
        self._base_url = URL(value)

    @property
    def auth(self) -> typing.Optional[Auth]:
        """
        Default authentication configuration to use for all requests.
        """
        return self._auth

    @auth.setter
    def auth(self, value: AuthTypes) -> None:
        self._auth = Auth(value)

    @property
    def cookies(self) -> Cookies:
        """
        Default cookies to use for all requests.
        """
        return self._cookies

    @cookies.setter
    def cookies(self, value: CookieTypes) -> None:
        self._cookies = Cookies(value)

    @property
    def headers(self) -> Headers:
        """
        Default headers to use for all requests.
        """
        return self._headers

    @headers.setter
    def headers(self, value: HeaderTypes) -> None:
        self._headers = Headers(value)

    @property
    def params(self) -> QueryParams:
        """
        Default query parameters to use for all requests.
        """
        return self._params

    @params.setter
    def params(self, value: QueryParamTypes) -> None:
        self._params = QueryParams(value)

    @property
    def verify(self) -> bool:
        """
        Enable TLS certificate verification.
        """
        return self._verify

    @verify.setter
    def verify(self, value: bool) -> None:
        self._verify = value

    @property
    def cert(self) -> typing.Optional[CertTypes]:
        """
        Client certificate to use for TLS authentication.
        """
        return self._cert

    @cert.setter
    def cert(self, value: CertTypes) -> None:
        self._cert = value

    @property
    def proxies(self) -> ProxiesTypes:
        """
        Default proxies to use for all requests.
        """
        return self._proxies

    @proxies.setter
    def proxies(self, value: ProxiesTypes) -> None:
        self._proxies = value

    @property
    def timeout(self) -> Timeout:
        """
        Default timeout for requests.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: TimeoutTypes) -> None:
        self._timeout = DEFAULT_TIMEOUT_CONFIG if value is USE_CLIENT_DEFAULT else value

    @property
    def limits(self) -> Limits:
        """
        Default limits to use for requests.
        """
        return self._limits

    @limits.setter
    def limits(self, value: Limits) -> None:
        self._limits = DEFAULT_LIMITS if value is None else value

    @property
    def extensions(self) -> RequestExtensions:
        """
        Default extensions to use for all requests.
        """
        return self._extensions

    @extensions.setter
    def extensions(self, value: RequestExtensions) -> None:
        self._extensions = value

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
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

        self._transport.__exit__(exc_type, exc_value, traceback)
        for proxy in self._mounts.values():
            if proxy is not None:
                proxy.__exit__(exc_type, exc_value, traceback)

    def __repr__(self) -> str:
        return f"<Client[{self._transport.__class__.__name__}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, Client) and self._transport == other._transport

    def __hash__(self) -> int:
        return hash(self._transport)

    @property
    def transport(self) -> BaseTransport:
        """
        The underlying HTTP transport.
        """
        return self._transport

    def __getattr__(self, name: str) -> typing.Callable[..., Response]:
        """
        Dynamically create methods for sending requests.
        """
        if name.startswith("__"):
            raise AttributeError(
                f"Unknown attribute '{name}'. Did you mean to send a request?"
            )

        def make_request(
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
            follow_redirects: typing.Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
            timeout: typing.Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
            extensions: typing.Optional[RequestExtensions] = None,
        ) -> Response:
            """
            Send a request.

            **Parameters**:

            * **method** – The HTTP method to use.
            * **url** – The URL to send the request to.
            * **content** – Raw bytes to send in the request body.
            * **data** – Form-encoded data to send in the request body.
            * **files** – Files to send in the request body.
            * **json** – JSON data to send in the request body.
            * **params** – Query parameters to send with the request.
            * **headers** – Headers to send with the request.
            * **cookies** – Cookies to send with the request.
            * **auth** – Authentication configuration to use for the request.
            * **follow_redirects** – Whether to automatically follow redirects.
            * **timeout** – Timeout for the request.
            * **extensions** – Extensions to use for the request.
            """
            return self.request(
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

        return make_request

    @property
    def _default_headers(self) -> Headers:
        headers = Headers(headers=self._headers, encoding=self._headers.encoding)
        if self._auth is not None:
            headers.update(self._auth.get_auth_headers(headers))
        return headers

    @property
    def _default_cookies(self) -> Cookies:
        cookies = Cookies(cookies=self._cookies)
        if self._auth is not None:
            cookies.update(self._auth.get_auth_cookies(cookies))
        return cookies

    @property
    def _default_auth(self) -> Auth:
        return Auth(self._auth) if self._auth is not None else None

    @property
    def _default_timeout(self) -> Timeout:
        return self._timeout if self._timeout is not USE_CLIENT_DEFAULT else None

    @property
    def _default_limits(self) -> Limits:
        return self._limits if self._limits is not None else None

    @property
    def _default_extensions(self) -> RequestExtensions:
        return self._extensions if self._extensions is not None else {}

    @property
    def _default_params(self) -> QueryParams:
        return self._params if self._params is not None else {}

    @property
    def _default_proxies(self) -> ProxiesTypes:
        return self._proxies if self._proxies is not None else {}

    @property
    def _default_verify(self) -> bool:
        return self._verify if self._verify is not None else True

    @property
    def _default_cert(self) -> CertTypes:
        return self._cert if self._cert is not None else None

    @property
    def _default_base_url(self) -> URL:
        return self._base_url if self._base_url is not None else ""

    @property
    def _default_headers_encoding(self) -> str:
        return self._headers.encoding if self._headers.encoding is not None else "ascii"

    def _get_transport(self, url: URL) -> BaseTransport:
        """
        Return the transport to use for a given URL.
        """
        if self._base_url is not None and self._base_url.origin == url.origin:
            return self._transport

        for prefix, transport in self._mounts.items():
            if url.path.startswith(prefix):
                return transport

        return self._transport

    def _get_proxy(self, url: URL) -> Proxy:
        """
        Return the proxy to use for a given URL.
        """
        if self._proxies is None:
            return None

        for prefix, proxy in self._proxies.items():
            if url.path.startswith(prefix):
                return proxy

        return self._proxies.get("")

    def _get_auth(self, url: URL) -> Auth:
        """
        Return the auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)

        return None

    def _get_cookies(self, url: URL) -> Cookies:
        """
        Return the cookies to use for a given URL.
        """
        if self._cookies is not None:
            return Cookies(self._cookies)

        return None

    def _get_timeout(self, url: URL) -> Timeout:
        """
        Return the timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout

        return None

    def _get_limits(self, url: URL) -> Limits:
        """
        Return the limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits

        return None

    def _get_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions

        return {}

    def _get_params(self, url: URL) -> QueryParams:
        """
        Return the params to use for a given URL.
        """
        if self._params is not None:
            return self._params

        return {}

    def _get_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies

        return {}

    def _get_verify(self, url: URL) -> bool:
        """
        Return the verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify

        return True

    def _get_cert(self, url: URL) -> CertTypes:
        """
        Return the cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert

        return None

    def _get_base_url(self, url: URL) -> URL:
        """
        Return the base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url

        return ""

    def _get_headers_encoding(self, url: URL) -> str:
        """
        Return the headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding

        return "ascii"

    def _get_default_headers(self, url: URL) -> Headers:
        """
        Return the default_headers to use for a given URL.
        """
        if self._auth is not None:
            return Headers(headers=self._auth.get_auth_headers(headers=self._headers), encoding=self._headers.encoding)
        return Headers(headers=self._headers, encoding=self._headers.encoding)

    def _get_default_cookies(self, url: URL) -> Cookies:
        """
        Return the default_cookies to use for a given URL.
        """
        if self._cookies is not None:
            return Cookies(cookies=self._cookies)
        return Cookies(cookies=None)

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to use for a given URL.
        """
        if self._headers.encoding is not None:
            return self._headers.encoding
        return "ascii"

    def _get_default_auth(self, url: URL) -> Auth:
        """
        Return the default_auth to use for a given URL.
        """
        if self._auth is not None:
            return Auth(self._auth)
        return None

    def _get_default_timeout(self, url: URL) -> Timeout:
        """
        Return the default_timeout to use for a given URL.
        """
        if self._timeout is not USE_CLIENT_DEFAULT:
            return self._timeout
        return None

    def _get_default_limits(self, url: URL) -> Limits:
        """
        Return the default_limits to use for a given URL.
        """
        if self._limits is not None:
            return self._limits
        return None

    def _get_default_extensions(self, url: URL) -> RequestExtensions:
        """
        Return the default_extensions to use for a given URL.
        """
        if self._extensions is not None:
            return self._extensions
        return {}

    def _get_default_params(self, url: URL) -> QueryParams:
        """
        Return the default_params to use for a given URL.
        """
        if self._params is not None:
            return self._params
        return {}

    def _get_default_proxies(self, url: URL) -> ProxiesTypes:
        """
        Return the default_proxies to use for a given URL.
        """
        if self._proxies is not None:
            return self._proxies
        return {}

    def _get_default_verify(self, url: URL) -> bool:
        """
        Return the default_verify to use for a given URL.
        """
        if self._verify is not None:
            return self._verify
        return True

    def _get_default_cert(self, url: URL) -> CertTypes:
        """
        Return the default_cert to use for a given URL.
        """
        if self._cert is not None:
            return self._cert
        return None

    def _get_default_base_url(self, url: URL) -> URL:
        """
        Return the default_base_url to use for a given URL.
        """
        if self._base_url is not None:
            return self._base_url
        return ""

    def _get_default_headers_encoding(self, url: URL) -> str:
        """
        Return the default_headers_encoding to