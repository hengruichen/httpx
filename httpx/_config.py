import logging
import ssl
import typing
from pathlib import Path

import certifi

from ._compat import set_minimum_tls_version_1_2
from ._models import Headers
from ._types import CertTypes, HeaderTypes, TimeoutTypes, URLTypes, VerifyTypes
from ._urls import URL

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


class SSLContext(ssl.SSLContext):
    DEFAULT_CA_BUNDLE_PATH = Path(certifi.where())

    def __init__(
        self,
        verify: VerifyTypes = True,
        cert: typing.Optional[CertTypes] = None,
    ) -> None:
        self.verify = verify
        set_minimum_tls_version_1_2(self)
        self.options |= ssl.OP_NO_COMPRESSION
        self.set_ciphers(DEFAULT_CIPHERS)

        logger.debug(
            "load_ssl_context verify=%r cert=%r",
            verify,
            cert,
        )

        if verify:
            self.load_ssl_context_verify(cert, verify)
        else:
            self.load_ssl_context_no_verify(cert)

    def load_ssl_context_no_verify(
        self, cert: typing.Optional[CertTypes]
    ) -> ssl.SSLContext:
        """
        Return an SSL context for unverified connections.
        """
        self.check_hostname = False
        self.verify_mode = ssl.CERT_NONE
        self._load_client_certs(cert)
        return self

    def load_ssl_context_verify(
        self, cert: typing.Optional[CertTypes], verify: VerifyTypes
    ) -> None:
        """
        Return an SSL context for verified connections.
        """
        if isinstance(verify, bool):
            ca_bundle_path = self.DEFAULT_CA_BUNDLE_PATH
        elif Path(verify).exists():
            ca_bundle_path = Path(verify)
        else:
            raise IOError(
                "Could not find a suitable TLS CA certificate bundle, "
                "invalid path: {}".format(verify)
            )

        self.verify_mode = ssl.CERT_REQUIRED
        self.check_hostname = True

        # Signal to server support for PHA in TLS 1.3. Raises an
        # AttributeError if only read-only access is implemented.
        try:
            self.post_handshake_auth = True
        except AttributeError:  # pragma: no cover
            pass

        # Disable using 'commonName' for SSLContext.check_hostname
        # when the 'subjectAltName' extension isn't available.
        try:
            self.hostname_checks_common_name = False
        except AttributeError:  # pragma: no cover
            pass

        if ca_bundle_path.is_file():
            cafile = str(ca_bundle_path)
            logger.debug("load_verify_locations cafile=%r", cafile)
            self.load_verify_locations(cafile=cafile)
        elif ca_bundle_path.is_dir():
            capath = str(ca_bundle_path)
            logger.debug("load_verify_locations capath=%r", capath)
            self.load_verify_locations(capath=capath)

        self._load_client_certs(cert)

    def _load_client_certs(self, cert: typing.Optional[CertTypes] = None) -> None:
        """
        Loads client certificates into our SSLContext object
        """
        if cert is not None:
            if isinstance(cert, str):
                self.load_cert_chain(certfile=cert)
            elif isinstance(cert, tuple) and len(cert) == 2:
                self.load_cert_chain(certfile=cert[0], keyfile=cert[1])
            elif isinstance(cert, tuple) and len(cert) == 3:
                self.load_cert_chain(
                    certfile=cert[0],
                    keyfile=cert[1],
                    password=cert[2],
                )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing.Any) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.verify == other.verify
            and self.options == other.options
            and self.set_ciphers(DEFAULT_CIPHERS)
        )

    def __repr__(self) -> str:
        return f"<SSLContext [verify={self.verify}]>"

    def __eq__(self, other: typing