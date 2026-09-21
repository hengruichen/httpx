import ssl
from pathlib import Path

import certifi
import pytest

import httpx


def test_load_ssl_config():
    context = httpx.SSLContext()
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_non_existing_path():
    with pytest.raises(IOError):
        httpx.SSLContext(verify="/path/to/nowhere")


def test_load_ssl_config_verify_existing_file():
    context = httpx.SSLContext(verify=certifi.where())
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_verify_directory():
    path = Path(certifi.where()).parent
    context = httpx.SSLContext(verify=str(path))
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


def test_load_ssl_config_cert_and_key(cert_pem_file, cert_private_key_file):
    context = httpx.SSLContext(cert=(cert_pem_file, cert_private_key_file))
    assert context.verify_mode == ssl.VerifyMode.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("password", [b"password", "password"])
def test_load_ssl_config_cert_and_enc