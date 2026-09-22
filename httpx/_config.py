import logging
import os
import ssl
import typing
from pathlib import Path

import certifi

from ._compat import set_minimum_tls_version_1_2
from ._models import Headers
from ._types import CertTypes, HeaderTypes, TimeoutTypes, URLTypes, VerifyTypes
from ._urls import URL
from ._utils import get_ca_bundle_from_env


SOCKET_OPTION = typing.Union[
    typing.Tuple[int, int, int],
    typing.Tuple[int, int, typing.Union[bytes, bytearray]],
    typing.Tuple[int, int, None, int],
]

DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)


logger = logging.getLogger("httpx")


class UnsetType:
    pass  # pragma: no cover


UNSET = UnsetType()


def create_ssl_context(
    cert: typing.Optional[CertTypes] = None,
    verify: VerifyTypes = True,
    trust_env: bool = True,
    http2: bool = False,
) -> ssl.SSLContext:
    return SSLConfig(
        cert=cert, verify=verify, trust_env=trust_env, http2=http2
    ).ssl_context


class SSLConfig:
    """
    SSL Configuration.
    """

    DEFAULT_CA_BUNDLE_PATH = Path(certifi.where())

    def __init__(
        self,
        *,
        cert: typing.Optional[CertTypes] = None,
        verify: VerifyTypes = True,
        trust_env: bool = True,
        http2: bool = False,
    ) -> None:
        self.cert = cert
        self.verify = verify
        self.trust_env = trust_env
        self.http2 = http2
        self.ssl_context = self.load_ssl_context()

    def load_ssl_context(self) -> ssl.SSLContext:
        logger.debug(
            "load_ssl_context verify=%r cert=%r trust_env=%r http2=%r",
            self.verify,
            self.cert,
            self.trust_env,
            self.http2,
        )

        if self.verify:
            return self.load_ssl_context_verify()
        return self.load_ssl_context_no_verify()

    def load_ssl_context_no_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        context = self._create_default_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self._load_client_certs(context)
        return context

    def load_ssl_context_verify(self) -> ssl.SSLContext:
        """
        Return an SSL context for verified connections.
        """
        if self.trust_env and self.verify is True:
            ca_bundle = get_ca_bundle_from_env()
            if ca_bundle is not None:
                self.verify = ca_bundle

        if isinstance(self.verify, ssl.SSLContext):
            # Allow passing in our own SSLContext object that's pre-configured.
            context = self.verify
            self._load_client_certs(context)
            return context
        elif isinstance(self.verify, bool):
            ca_bundle_path = self.DEFAULT_CA_BUNDLE_PATH
        elif Path(self.verify).exists():
            ca_bundle_path = Path(self.verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(self.verify)
            )

        context = self._create_default_ssl_context()
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True

        # Signal to server support for PHA in TLS 1.3. Raises an
        # AttributeError if only read-only access is implemented.
        try:
            context.post_handshake_auth = True
        except AttributeError:  # pragma: no cover
            pass

        # Disable using 'commonName' for SSLContext.check_hostname
        # when the 'subjectAltName' extension isn't available.
        try:
            context.hostname_checks_common_name = False
        except AttributeError:  # pragma: no cover
            pass

        # Load the CA certificate bundle.
        context.load_verify_locations(cafile=ca_bundle_path)

        # Load client certificates and keys.
        self._load_client_certs(context)

        return context

    def _create_default_ssl_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        set_minimum_tls_version_1_2(context)
        return context

    def _load_client_certs(self, context: ssl.SSLContext) -> None:
        if isinstance(self.cert, (list, tuple)):
            if len(self.cert) == 2:
                cert_path, key_path = self.cert
                context.load_cert_chain(cert_path, keyfile=key_path)
            elif len(self.cert) == 3:
                cert_path, key_path, key_password = self.cert
                context.load_cert_chain(
                    cert_path, keyfile=key_path, password=key_password
                )
            else:
                raise ValueError("Invalid cert parameter")
        elif isinstance(self.cert, (str, Path)):
            context.load_cert_chain(certfile=self.cert)
