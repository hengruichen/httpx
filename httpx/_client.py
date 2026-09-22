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
        seconds = self._timer.elapsed()
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


class BoundSyncResponse(Response):
    """
    A response that is bound to a given client instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self,
        stream: SyncByteStream,
        request: Request,
        *,
        status_code: int,
        headers: Headers,
        url: URL,
        extensions: ResponseExtensions,
        timer: Timer,
    ) -> None:
        self._stream = stream
        self._request = request
        self._status_code = status_code
        self._headers = headers
        self._url = url
        self._extensions = extensions
        self._elapsed = None
        self._timer = timer

    @property
    def elapsed(self) -> datetime.timedelta:
        """
        The duration of the request, as a `datetime.timedelta` object.
        """
        if self._elapsed is None:
            seconds = self._timer.sync_elapsed()
            self._elapsed = datetime.timedelta(seconds=seconds)
        return self._elapsed

    def __enter__(self) -> "BoundSyncResponse":
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response stream.
        """
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def __repr__(self) -> str:
        return (
            "<BoundSyncResponse [%s] %s>"
            % (self.status_code, self.request.url)
        )


class BoundAsyncResponse(Response):
    """
    A response that is bound to a given client instance, and that
    ensures the `response.elapsed` is set once the response is closed.
    """

    def __init__(
        self,
        stream: AsyncByteStream,
        request: Request,
        *,
        status_code: int,
        headers: Headers,
        url: URL,
        extensions: ResponseExtensions,
        timer: Timer,
    ) -> None:
        self._stream = stream
        self._request = request
        self._status_code = status_code
        self._headers = headers
        self._url = url
        self._extensions = extensions
        self._elapsed = None
        self._timer = timer

    @property
    def elapsed(self) -> datetime.timedelta:
        """
        The duration of the request, as a `datetime.timedelta` object.
        """
        if self._elapsed is None:
            seconds = self._timer.elapsed()
            self._elapsed = datetime.timedelta(seconds=seconds)
        return self._elapsed

    async def __aenter__(self) -> "BoundAsyncResponse":
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """
        Close the response stream.
        """
        if self._stream is not None:
            await self._stream.aclose()
            self._stream = None

    def __repr__(self) -> str:
        return (
            "<BoundAsyncResponse [%s] %s>"
            % (self.status_code, self.request.url)
        )


class Client:
    """
    The `Client` is the primary interface for making requests.

    A client instance is a context manager, and should be used as such:

    .. code-block:: python

        with Client() as client:
            response = client.get("https://example.com/")

    """

    def __init__(
        self,
        *,
        base_url:***REDACTED***@property
    def base_url(self) -> URL:
        """
        The base URL used when constructing absolute URLs from relative URLs.
        """
        return self._base_url

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
        """
        return self._limits

    @property
    def proxies(self) -> ProxiesTypes:
        """
        The default proxies for requests.
        """
        return self._proxies

    @property
    def auth(self) -> Auth:
        """
        The default authentication for requests.
        """
        return self._auth

    @property
    def follow_redirects(self) -> bool:
        """
        Whether or not to automatically follow HTTP redirects.
        """
        return self._follow_redirects

    @property
    def verify(self) -> bool:
        """
        Whether or not to verify SSL certificates.
        """
        return self._verify

    @property
    def timeout(self) -> Timeout:
        """
        The default timeout for requests.
        """
        return self._timeout

    @property
    def limits(self) -> Limits:
        """
        The default limits for requests.
       