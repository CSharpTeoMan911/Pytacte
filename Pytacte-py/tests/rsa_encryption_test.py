import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from utils import Crytography
from utils.Crytography import RSA_Crypto
from utils.GoogleSecretsManager import ReturnValue


@pytest.fixture
def crypto():
    return RSA_Crypto()


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_generates_password_with_requested_length_and_allowed_characters(crypto):
    password = crypto.__cryptographycally_secure_random_password_generator__(64)
    allowed_characters = (
        crypto.LOWERCASE_LETTERS
        + crypto.UPPERCASE_LETTERS
        + crypto.SYMBOLS
        + crypto.NUMBERS
    )

    assert len(password) == 64
    assert all(character in allowed_characters for character in password)


def test_generates_4096_bit_rsa_private_key(crypto):
    key = crypto.generate_rsa_key()

    assert isinstance(key, rsa.RSAPrivateKey)
    assert key.key_size == 4096


def test_serialises_password_protected_rsa_key(crypto, rsa_key):
    auth_result = ReturnValue("Authentication successful", True, None)
    secret_result = ReturnValue("Secret addition successful", True, None)

    with (
        patch.object(Crytography, "GoogleSecretsManager") as secrets_manager,
        patch.object(
            crypto,
            "__cryptographycally_secure_random_password_generator__",
            return_value="test-password",
        ),
    ):
        manager = secrets_manager.return_value
        manager.verifyGoogleCloudAuthentication.return_value = auth_result
        manager.setSecret = AsyncMock(return_value=secret_result)

        public_pem, private_pem = asyncio.run(
            crypto.serialise_rsa_key_pair(passwordless=False, key=rsa_key)
        )

        manager.setSecret.assert_awaited_once_with(
            name="private_key_password", secret="test-password"
        )

    loaded_public_key = serialization.load_pem_public_key(public_pem)
    loaded_private_key = serialization.load_pem_private_key(
        private_pem,
        password=b"test-password",
    )
    assert isinstance(loaded_public_key, rsa.RSAPublicKey)
    assert isinstance(loaded_private_key, rsa.RSAPrivateKey)
    assert loaded_public_key.public_numbers() == rsa_key.public_key().public_numbers()
    assert loaded_private_key.private_numbers() == rsa_key.private_numbers()


def test_serialises_unencrypted_rsa_key_when_passwordless(crypto, rsa_key):
    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        manager = secrets_manager.return_value
        manager.setSecret = AsyncMock()
        public_pem, private_pem = asyncio.run(
            crypto.serialise_rsa_key_pair(passwordless=True, key=rsa_key)
        )
        manager.verifyGoogleCloudAuthentication.assert_not_called()
        manager.setSecret.assert_not_awaited()

    loaded_public_key = serialization.load_pem_public_key(public_pem)
    loaded_private_key = serialization.load_pem_private_key(private_pem, password=None)
    assert isinstance(loaded_public_key, rsa.RSAPublicKey)
    assert isinstance(loaded_private_key, rsa.RSAPrivateKey)
    assert loaded_public_key.public_numbers() == rsa_key.public_key().public_numbers()
    assert loaded_private_key.private_numbers() == rsa_key.private_numbers()


def test_rejects_serialisation_when_google_authentication_fails(crypto, rsa_key):
    auth_result = ReturnValue("ADC credentials unavailable", False, None)

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        manager = secrets_manager.return_value
        manager.verifyGoogleCloudAuthentication.return_value = auth_result
        manager.setSecret = AsyncMock()

        with pytest.raises(RuntimeError, match="ADC credentials unavailable"):
            asyncio.run(
                crypto.serialise_rsa_key_pair(passwordless=False, key=rsa_key)
            )

        manager.setSecret.assert_not_awaited()


def test_writes_rsa_key_to_data_file(crypto, rsa_key, tmp_path, monkeypatch):
    pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    data_path = tmp_path / "data"
    data_path.mkdir()
    monkeypatch.chdir(tmp_path)

    result = crypto.write_rsa_key_to_file("private.pem", pem)

    assert result == data_path / "private.pem"
    assert result.read_bytes() == pem


def test_writes_certificate_from_rsa_key_pair(crypto, rsa_key, tmp_path, monkeypatch):
    public_pem = rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    data_path = tmp_path / "data"
    data_path.mkdir()
    monkeypatch.chdir(tmp_path)

    certificate_path = asyncio.run(
        crypto.write_keys_to_cert("server_cert.pem", public_pem, private_pem)
    )

    assert Path(certificate_path) == data_path / "server_cert.pem"
    certificate = x509.load_pem_x509_certificate(Path(certificate_path).read_bytes())
    assert (
        certificate.public_key().public_numbers()
        == rsa_key.public_key().public_numbers()
    )


def test_writes_certificate_from_password_protected_rsa_key_pair(
    crypto, rsa_key, tmp_path, monkeypatch
):
    public_pem = rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"test-password"),
    )
    data_path = tmp_path / "data"
    data_path.mkdir()
    monkeypatch.chdir(tmp_path)

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        manager = secrets_manager.return_value
        manager.getSecret = AsyncMock(
            return_value=ReturnValue("Secret retrieval successful", True, "test-password")
        )
        certificate_path = asyncio.run(
            crypto.write_keys_to_cert(
                "server_cert.pem", public_pem, private_pem, False
            )
        )
        manager.getSecret.assert_awaited_once_with("private_key_password")

    assert Path(certificate_path) == data_path / "server_cert.pem"
    certificate = x509.load_pem_x509_certificate(Path(certificate_path).read_bytes())
    assert (
        certificate.public_key().public_numbers()
        == rsa_key.public_key().public_numbers()
    )


def test_rejects_non_rsa_public_key_when_writing_certificate(
    crypto, rsa_key
):
    ec_public_pem = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    with pytest.raises(TypeError, match="The public key is not an RSA public key"):
        asyncio.run(
            crypto.write_keys_to_cert("server_cert.pem", ec_public_pem, private_pem)
        )


def test_rejects_non_rsa_private_key_when_writing_certificate(
    crypto, rsa_key
):
    public_pem = rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    ec_private_pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    with pytest.raises(TypeError, match="The private key is not an RSA private key"):
        asyncio.run(
            crypto.write_keys_to_cert("server_cert.pem", public_pem, ec_private_pem)
        )
