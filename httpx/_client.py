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
    An HTTP client.

    **Parameters:**

    - **base_url** -- An optional base URL to use for all requests sent from
      this client instance. If provided, all requests will be assumed to be
      relative to this URL, and will have this URL prepended to them before
      sending.
    - **transport** -- An optional transport implementation to use for sending
      HTTP requests. Defaults to `httpx.HTTPTransport`.
    - **limits** -- An optional `Limits` instance to use for configuring
      connection limits on the underlying transport.
    - **follow_redirects** -- An optional boolean indicating whether redirects
      should be automatically followed. Defaults to `False`.
    - **auth** -- An optional `Auth` instance to use for authenticating
      requests. May also be provided as a callable, string, or tuple.
    - **proxy** -- An optional `Proxy` instance to use for configuring
      proxies. May also be provided as a string.
    - **timeout** -- An optional `Timeout` instance to use for configuring
      timeouts on requests.
    - **verify** -- An optional `VerifyTypes` value to use for configuring
      TLS verification.
    - **cert** -- An optional `CertTypes` value to use for configuring TLS
      client certificates.
    - **http2** -- An optional boolean indicating whether HTTP/2 should be
      enabled. Defaults to `True`.
    - **http2_prior_knowledge** -- An optional boolean indicating whether to
      enable HTTP/2 without HTTP/1.1 Upgrade. Defaults to `False`.
    - **max_redirects** -- An optional integer indicating the maximum number of
      redirects to follow. Defaults to `DEFAULT_MAX_REDIRECTS`.
    - **dispatch** -- An optional `Dispatch` instance to use for configuring
      request routing.
    - **event_hooks** -- An optional `EventHooks` to use for configuring event
      hooks.
    - **extensions** -- An optional `Extensions` to use for configuring
      extensions.
    """

    def __init__(
        self,
        *,
        base_url: typing.Optional[URLTypes] = None,
        transport: typing.Optional[BaseTransport] = None,
        limits: typing.Optional[Limits] = None,
        follow_redirects: typing.Optional[bool] = None,
        auth: typing.Optional[AuthTypes] = None,
        proxy: typing.Optional[ProxyTypes] = None,
        timeout: typing.Optional[TimeoutTypes] = None,
        verify: typing.Optional[VerifyTypes] = None,
        cert: typing.Optional[CertTypes] = None,
        http2: typing.Optional[bool] = None,
        http2_prior_knowledge: typing.Optional[bool] = None,
        max_redirects: typing.Optional[int] = None,
        dispatch: typing.Optional["Dispatch"] = None,
        event_hooks: typing.Optional[EventHooks] = None,
        extensions: typing.Optional[Extensions] = None,
    ) -> None:
        if dispatch is None:
            from ._dispatch import Dispatcher

            dispatch = Dispatcher()

        if event_hooks is None:
            from ._events import Events

            event_hooks = Events()

        if extensions is None:
            from ._extensions import Extensions

            extensions = Extensions()

        if max_redirects is None:
            max_redirects = DEFAULT_MAX_REDIRECTS

        if http2 is None:
            http2 = True

        if http2_prior_knowledge is None:
            http2_prior_knowledge = False

        if timeout is None:
            timeout = DEFAULT_TIMEOUT_CONFIG

        if limits is None:
            limits = DEFAULT_LIMITS

        self._state = ClientState.UNOPENED
        self._base_url = URL(base_url) if base_url is not None else None
        self._transport = transport
        self._limits = limits
        self._follow_redirects = follow_redirects
        self._auth = auth
        self._proxy = proxy
        self._timeout = timeout
        self._verify = verify
        self._cert = cert
        self._http2 = http2
        self._http2_prior_knowledge = http2_prior_knowledge
        self._max_redirects = max_redirects
        self._dispatch = dispatch
        self._event_hooks = event_hooks
        self._extensions = extensions

        self._mounts = {}

    @property
    def base_url(self) -> typing.Optional[URL]:
        """
        The base URL for the client.
        """
        return self._base_url

    @property
    def transport(self) -> BaseTransport:
        """
        The underlying transport instance.
        """
        return self._transport

    @property
    def limits(self) -> Limits:
        """
        The connection limits configured on the client.
        """
        return self._limits

    @property
    def follow_redirects(self) -> bool:
        """
        Whether redirects are automatically followed.
        """
        return self._follow_redirects

    @property
    def auth(self) -> typing.Optional[Auth]:
        """
        The configured auth instance.
        """
        return self._auth

    @property
    def proxy(self) -> typing.Optional[Proxy]:
        """
        The configured proxy instance.
        """
        return self._proxy

    @property
    def timeout(self) -> Timeout:
        """
        The configured timeout instance.
        """
        return self._timeout

    @property
    def verify(self) -> VerifyTypes:
        """
        The configured TLS verification value.
        """
        return self._verify

    @property
    def cert(self) -> CertTypes:
        """
        The configured TLS certificate value.
        """
        return self._cert

    @property
    def http2(self) -> bool:
        """
        Whether HTTP/2 is enabled.
        """
        return self._http2

    @property
    def http2_prior_knowledge(self) -> bool:
        """
        Whether HTTP/2 is enabled without HTTP/1.1 Upgrade.
        """
        return self._http2_prior_knowledge

    @property
    def max_redirects(self) -> int:
        """
        The configured maximum number of redirects.
        """
        return self._max_redirects

    @property
    def dispatch(self) -> "Dispatch":
        """
        The configured dispatch instance.
        """
        return self._dispatch

    @property
    def event_hooks(self) -> EventHooks:
        """
        The configured event hooks.
        """
        return self._event_hooks

    @property
    def extensions(self) -> Extensions:
        """
        The configured extensions.
        """
        return self._extensions

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

        if self._transport is None:
            self._transport = self._get_transport()

        if self._transport is not None:
            self._transport.__enter__()

        for proxy in self._mounts.values():
            if proxy is not None:
                if proxy.transport is not None:
                    proxy.transport.__enter__()

        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

        if self._transport is not None:
            self._transport.__exit__(exc_type, exc_value, traceback)

        for proxy in self._mounts.values():
            if proxy is not None and proxy.transport is not None:
                proxy.transport.__exit__(exc_type, exc_value, traceback)

    async def __aenter__(self: U) -> U:
        if self._state != ClientState.UNOPENED:
            msg = {
                ClientState.OPENED: "Cannot open a client instance more than once.",
                ClientState.CLOSED: (
                    "Cannot reopen a client instance, once it has been closed."
                ),
            }[self._state]
            raise RuntimeError(msg)

        self._state = ClientState.OPENED

        if self._transport is None:
            self._transport = await self._aget_transport()

        if self._transport is not None:
            await self._transport.__aenter__()

        for proxy in self._mounts.values():
            if proxy is not None:
                if proxy.transport is not None:
                    await proxy.transport.__aenter__()

        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]] = None,
        exc_value: typing.Optional[BaseException] = None,
        traceback: typing.Optional[TracebackType] = None,
    ) -> None:
        self._state = ClientState.CLOSED

        if self._transport is not None:
            await self._transport.__aexit__(exc_type, exc_value, traceback)

        for proxy in self._mounts.values():
            if proxy is not None and proxy.transport is not None:
                await proxy.transport.__aexit__(exc_type, exc_value, traceback)

    def _get_transport(self) -> BaseTransport:
        if self._transport is not None:
            return self._transport

        if self._proxy is not None:
            return self._get_proxy_transport()

        return self._get_default_transport()

    async def _aget_transport(self) -> AsyncBaseTransport:
        if self._transport is not None:
            return self._transport

        if self._proxy is not None:
            return await self._aget_proxy_transport()

        return await self._aget_default_transport()

    def _get_default_transport(self) -> HTTPTransport:
        return HTTPTransport(
            limits=self._limits,
            follow_redirects=self._follow_redirects,
            auth=self._auth,
            proxy=self._proxy,
            timeout=self._timeout,
            verify=self._verify,
            cert=self._cert,
            http2=self._http2,
            http2_prior_knowledge=self._http2_prior_knowledge,
            dispatch=self._dispatch,
            event_hooks=self._event_hooks,
            extensions=self._extensions,
        )

    async def _aget_default_transport(self) -> AsyncHTTPTransport:
        return AsyncHTTPTransport(
            limits=self._limits,
            follow_redirects=self._follow_redirects,
            auth=self._auth,
            proxy=self._proxy,
            timeout=self._timeout,
            verify=self._verify,
            cert=self._cert,
            http2=self._http2,
            http2_prior_knowledge=self._http2_prior_knowledge,
            dispatch=self._dispatch,
            event_hooks=self._event_hooks,
            extensions=self._extensions,
        )

    def _get_proxy_transport(self) -> ASGITransport:
        return ASGITransport(
            limits=self._limits,
            auth=self._auth,
            proxy=self._proxy,
            timeout=self._timeout,
            verify=self._verify,
            cert=self._cert,
            http2=self._http2,
            http2_prior_knowledge=self._http2_prior_knowledge,
            dispatch=self._dispatch,
            event_hooks=self._event_hooks,
            extensions=self._extensions,
        )

    async def _aget_proxy_transport(self) -> ASGITransport:
        return ASGITransport(
            limits=self._limits,
            auth=self._auth,
            proxy=self._proxy,
            timeout=self._timeout,
            verify=self._verify,
            cert=self._cert,
            http2=self._http2,
            http2_prior_knowledge=self._http2_prior_knowledge,
            dispatch=self._dispatch,
            event_hooks=self._event_hooks,
            extensions=self._extensions,
        )

    def _get_transport_for_url(self, url: URL) -> BaseTransport:
        if self._proxy is not None:
            return self._get_proxy_transport()

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]

        return self._get_default_transport()

    async def _aget_transport_for_url(self, url: URL) -> AsyncBaseTransport:
        if self._proxy is not None:
            return await self._aget_proxy_transport()

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]

        return await self._aget_default_transport()

    def _set_transport_for_url(self, url: URL, transport: BaseTransport) -> None:
        if self._mounts.get(url.scheme) is not None:
            raise RuntimeError(
                f"Cannot override the transport for the '{url.scheme}' URL scheme."
            )

        self._mounts[url.scheme] = transport

    async def _aset_transport_for_url(
        self, url: URL, transport: AsyncBaseTransport
    ) -> None:
        if self._mounts.get(url.scheme) is not None:
            raise RuntimeError(
                f"Cannot override the transport for the '{url.scheme}' URL scheme."
            )

        self._mounts[url.scheme] = transport

    def _get_auth_for_url(self, url: URL) -> Auth:
        if self._auth is not None:
            return self._auth

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._auth

        return None

    async def _aget_auth_for_url(self, url: URL) -> Auth:
        if self._auth is not None:
            return self._auth

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_auth_for_url(url)

        return None

    def _set_auth_for_url(self, url: URL, auth: Auth) -> None:
        if self._auth is not None:
            raise RuntimeError(
                "Cannot override the auth for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_auth_for_url(url, auth)
            return

        self._auth = auth

    async def _aset_auth_for_url(self, url: URL, auth: Auth) -> None:
        if self._auth is not None:
            raise RuntimeError(
                "Cannot override the auth for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_auth_for_url(url, auth)
            return

        self._auth = auth

    def _get_proxy_for_url(self, url: URL) -> Proxy:
        if self._proxy is not None:
            return self._proxy

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._proxy

        return None

    async def _aget_proxy_for_url(self, url: URL) -> Proxy:
        if self._proxy is not None:
            return self._proxy

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_proxy_for_url(url)

        return None

    def _set_proxy_for_url(self, url: URL, proxy: Proxy) -> None:
        if self._proxy is not None:
            raise RuntimeError(
                "Cannot override the proxy for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_proxy_for_url(url, proxy)
            return

        self._proxy = proxy

    async def _aset_proxy_for_url(self, url: URL, proxy: Proxy) -> None:
        if self._proxy is not None:
            raise RuntimeError(
                "Cannot override the proxy for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_proxy_for_url(url, proxy)
            return

        self._proxy = proxy

    def _get_timeout_for_url(self, url: URL) -> Timeout:
        if self._timeout is not None:
            return self._timeout

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._timeout

        return None

    async def _aget_timeout_for_url(self, url: URL) -> Timeout:
        if self._timeout is not None:
            return self._timeout

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_timeout_for_url(url)

        return None

    def _set_timeout_for_url(self, url: URL, timeout: Timeout) -> None:
        if self._timeout is not None:
            raise RuntimeError(
                "Cannot override the timeout for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_timeout_for_url(url, timeout)
            return

        self._timeout = timeout

    async def _aset_timeout_for_url(self, url: URL, timeout: Timeout) -> None:
        if self._timeout is not None:
            raise RuntimeError(
                "Cannot override the timeout for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_timeout_for_url(url, timeout)
            return

        self._timeout = timeout

    def _get_verify_for_url(self, url: URL) -> VerifyTypes:
        if self._verify is not None:
            return self._verify

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._verify

        return None

    async def _aget_verify_for_url(self, url: URL) -> VerifyTypes:
        if self._verify is not None:
            return self._verify

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_verify_for_url(url)

        return None

    def _set_verify_for_url(self, url: URL, verify: VerifyTypes) -> None:
        if self._verify is not None:
            raise RuntimeError(
                "Cannot override the verify value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_verify_for_url(url, verify)
            return

        self._verify = verify

    async def _aset_verify_for_url(self, url: URL, verify: VerifyTypes) -> None:
        if self._verify is not None:
            raise RuntimeError(
                "Cannot override the verify value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_verify_for_url(url, verify)
            return

        self._verify = verify

    def _get_cert_for_url(self, url: URL) -> CertTypes:
        if self._cert is not None:
            return self._cert

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._cert

        return None

    async def _aget_cert_for_url(self, url: URL) -> CertTypes:
        if self._cert is not None:
            return self._cert

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_cert_for_url(url)

        return None

    def _set_cert_for_url(self, url: URL, cert: CertTypes) -> None:
        if self._cert is not None:
            raise RuntimeError(
                "Cannot override the cert value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_cert_for_url(url, cert)
            return

        self._cert = cert

    async def _aset_cert_for_url(self, url: URL, cert: CertTypes) -> None:
        if self._cert is not None:
            raise RuntimeError(
                "Cannot override the cert value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_cert_for_url(url, cert)
            return

        self._cert = cert

    def _get_http2_for_url(self, url: URL) -> bool:
        if self._http2 is not None:
            return self._http2

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._http2

        return None

    async def _aget_http2_for_url(self, url: URL) -> bool:
        if self._http2 is not None:
            return self._http2

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_http2_for_url(url)

        return None

    def _set_http2_for_url(self, url: URL, http2: bool) -> None:
        if self._http2 is not None:
            raise RuntimeError(
                "Cannot override the http2 value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_http2_for_url(url, http2)
            return

        self._http2 = http2

    async def _aset_http2_for_url(self, url: URL, http2: bool) -> None:
        if self._http2 is not None:
            raise RuntimeError(
                "Cannot override the http2 value for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_http2_for_url(url, http2)
            return

        self._http2 = http2

    def _get_http2_prior_knowledge_for_url(self, url: URL) -> bool:
        if self._http2_prior_knowledge is not None:
            return self._http2_prior_knowledge

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._http2_prior_knowledge

        return None

    async def _aget_http2_prior_knowledge_for_url(
        self, url: URL
    ) -> bool:
        if self._http2_prior_knowledge is not None:
            return self._http2_prior_knowledge

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_http2_prior_knowledge_for_url(
                url
            )

        return None

    def _set_http2_prior_knowledge_for_url(
        self, url: URL, http2_prior_knowledge: bool
    ) -> None:
        if self._http2_prior_knowledge is not None:
            raise RuntimeError(
                "Cannot override the http2_prior_knowledge value for the "
                "default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_http2_prior_knowledge_for_url(
                url, http2_prior_knowledge
            )
            return

        self._http2_prior_knowledge = http2_prior_knowledge

    async def _aset_http2_prior_knowledge_for_url(
        self, url: URL, http2_prior_knowledge: bool
    ) -> None:
        if self._http2_prior_knowledge is not None:
            raise RuntimeError(
                "Cannot override the http2_prior_knowledge value for the "
                "default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_http2_prior_knowledge_for_url(
                url, http2_prior_knowledge
            )
            return

        self._http2_prior_knowledge = http2_prior_knowledge

    def _get_max_redirects_for_url(self, url: URL) -> int:
        if self._max_redirects is not None:
            return self._max_redirects

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._max_redirects

        return None

    async def _aget_max_redirects_for_url(self, url: URL) -> int:
        if self._max_redirects is not None:
            return self._max_redirects

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_max_redirects_for_url(url)

        return None

    def _set_max_redirects_for_url(self, url: URL, max_redirects: int) -> None:
        if self._max_redirects is not None:
            raise RuntimeError(
                "Cannot override the max_redirects value for the "
                "default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_max_redirects_for_url(url, max_redirects)
            return

        self._max_redirects = max_redirects

    async def _aset_max_redirects_for_url(
        self, url: URL, max_redirects: int
    ) -> None:
        if self._max_redirects is not None:
            raise RuntimeError(
                "Cannot override the max_redirects value for the "
                "default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_max_redirects_for_url(url, max_redirects)
            return

        self._max_redirects = max_redirects

    def _get_dispatch_for_url(self, url: URL) -> "Dispatch":
        if self._dispatch is not None:
            return self._dispatch

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._dispatch

        return None

    async def _aget_dispatch_for_url(self, url: URL) -> "Dispatch":
        if self._dispatch is not None:
            return self._dispatch

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_dispatch_for_url(url)

        return None

    def _set_dispatch_for_url(self, url: URL, dispatch: "Dispatch") -> None:
        if self._dispatch is not None:
            raise RuntimeError(
                "Cannot override the dispatch for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_dispatch_for_url(url, dispatch)
            return

        self._dispatch = dispatch

    async def _aset_dispatch_for_url(self, url: URL, dispatch: "Dispatch") -> None:
        if self._dispatch is not None:
            raise RuntimeError(
                "Cannot override the dispatch for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_dispatch_for_url(url, dispatch)
            return

        self._dispatch = dispatch

    def _get_event_hooks_for_url(self, url: URL) -> EventHooks:
        if self._event_hooks is not None:
            return self._event_hooks

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._event_hooks

        return None

    async def _aget_event_hooks_for_url(self, url: URL) -> EventHooks:
        if self._event_hooks is not None:
            return self._event_hooks

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_event_hooks_for_url(url)

        return None

    def _set_event_hooks_for_url(self, url: URL, event_hooks: EventHooks) -> None:
        if self._event_hooks is not None:
            raise RuntimeError(
                "Cannot override the event_hooks for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_event_hooks_for_url(url, event_hooks)
            return

        self._event_hooks = event_hooks

    async def _aset_event_hooks_for_url(
        self, url: URL, event_hooks: EventHooks
    ) -> None:
        if self._event_hooks is not None:
            raise RuntimeError(
                "Cannot override the event_hooks for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_event_hooks_for_url(url, event_hooks)
            return

        self._event_hooks = event_hooks

    def _get_extensions_for_url(self, url: URL) -> Extensions:
        if self._extensions is not None:
            return self._extensions

        if self._mounts.get(url.scheme) is not None:
            return self._mounts[url.scheme]._extensions

        return None

    async def _aget_extensions_for_url(self, url: URL) -> Extensions:
        if self._extensions is not None:
            return self._extensions

        if self._mounts.get(url.scheme) is not None:
            return await self._mounts[url.scheme]._aget_extensions_for_url(url)

        return None

    def _set_extensions_for_url(self, url: URL, extensions: Extensions) -> None:
        if self._extensions is not None:
            raise RuntimeError(
                "Cannot override the extensions for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            self._mounts[url.scheme]._set_extensions_for_url(url, extensions)
            return

        self._extensions = extensions

    async def _aset_extensions_for_url(
        self, url: URL, extensions: Extensions
    ) -> None:
        if self._extensions is not None:
            raise RuntimeError(
                "Cannot override the extensions for the default URL scheme."
            )

        if self._mounts.get(url.scheme) is not None:
            await self._mounts[url.scheme]._aset_extensions_for_url(url, extensions)
            return

        self._extensions = extensions

    def _get_transport_for_request(self, request: Request) -> BaseTransport:
        return self._get_transport_for_url(request.url)

    async def _aget_transport_for_request(
        self, request: Request
    ) -> AsyncBaseTransport:
        return await self._aget_transport_for_url(request.url)

    def _set_transport_for_request(
        self, request: Request, transport: BaseTransport
    ) -> None:
        self._set_transport_for_url(request.url, transport)

    async def _aset_transport_for_request(
        self, request: Request, transport: AsyncBaseTransport
    ) -> None:
        await self._aset_transport_for_url(request.url, transport)

    def _get_auth_for_request(self, request: Request) -> Auth:
        return self._get_auth_for_url(request.url)

    async def _aget_auth_for_request(self, request: Request) -> Auth:
        return await self._aget_auth_for_url(request.url)

    def _set_auth_for_request(self, request: Request, auth: Auth) -> None:
        self._set_auth_for_url(request.url, auth)

    async def _aset_auth_for_request(self, request: Request, auth: Auth) -> None:
        await self._aset_auth_for_url(request.url, auth)

    def _get_proxy_for_request(self, request: Request) -> Proxy:
        return self._get_proxy_for_url(request.url)

    async def _aget_proxy_for_request(self, request: Request) -> Proxy:
        return await self._aget_proxy_for_url(request.url)

    def _set_proxy_for_request(self, request: Request, proxy: Proxy) -> None:
        self._set_proxy_for_url(request.url, proxy)

    async def _aset_proxy_for_request(self, request: Request, proxy: Proxy) -> None:
        await self._aset_proxy_for_url(request.url, proxy)

    def _get_timeout_for_request(self, request: Request) -> Timeout:
        return self._get_timeout_for_url(request.url)

    async def _aget_timeout_for_request(self, request: Request) -> Timeout:
        return await self._aget_timeout_for_url(request.url)

    def _set_timeout_for_request(self, request: Request, timeout: Timeout) -> None:
        self._set_timeout_for_url(request.url, timeout)

    async def _aset_timeout_for_request(
        self, request: Request, timeout: Timeout
    ) -> None:
        await self._aset_timeout_for_url(request.url, timeout)

    def _get_verify_for_request(self, request: Request) -> VerifyTypes:
        return self._get_verify_for_url(request.url)

    async def _aget_verify_for_request(self, request: Request) -> VerifyTypes:
        return await self._aget_verify_for_url(request.url)

    def _set_verify_for_request(self, request: Request, verify: VerifyTypes) -> None:
        self._set_verify_for_url(request.url, verify)

    async def _aset_verify_for_request(
        self, request: Request, verify: VerifyTypes
    ) -> None:
        await self._aset_verify_for_url(request.url, verify)

    def _get_cert_for_request(self, request: Request) -> CertTypes:
        return self._get_cert_for_url(request.url)

    async def _aget_cert_for_request(self, request: Request) -> CertTypes:
        return await self._aget_cert_for_url(request.url)

    def _set_cert_for_request(self, request: Request, cert: CertTypes) -> None:
        self._set_cert_for_url(request.url, cert)

    async def _aset_cert_for_request(self, request: Request, cert: CertTypes) -> None:
        await self._