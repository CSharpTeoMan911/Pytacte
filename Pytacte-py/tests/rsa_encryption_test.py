import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from utils import Crytography
from utils.Crytography import RSA_Crypto


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
    auth_result = Mock(successful=True)

    with (
        patch.object(Crytography, "GoogleSecretsManager") as secrets_manager,
        patch.object(
            crypto,
            "__cryptographycally_secure_random_password_generator__",
            return_value="test-password",
        ),
    ):
        secrets_manager.return_value.verifyGoogleCloudAuthentication.return_value = (
            auth_result
        )
        public_pem, private_pem = crypto.serialise_rsa_key(
            passwordless=False,
            key=rsa_key,
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
    auth_result = Mock(successful=True)

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        secrets_manager.return_value.verifyGoogleCloudAuthentication.return_value = (
            auth_result
        )
        public_pem, private_pem = crypto.serialise_rsa_key(
            passwordless=True,
            key=rsa_key,
        )

    loaded_public_key = serialization.load_pem_public_key(public_pem)
    loaded_private_key = serialization.load_pem_private_key(private_pem, password=None)
    assert isinstance(loaded_public_key, rsa.RSAPublicKey)
    assert isinstance(loaded_private_key, rsa.RSAPrivateKey)
    assert loaded_public_key.public_numbers() == rsa_key.public_key().public_numbers()
    assert loaded_private_key.private_numbers() == rsa_key.private_numbers()


def test_rejects_serialisation_when_google_authentication_fails(crypto, rsa_key):
    auth_result = Mock(
        successful=False,
        message="ADC credentials unavailable",
    )

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        secrets_manager.return_value.verifyGoogleCloudAuthentication.return_value = (
            auth_result
        )

        with pytest.raises(RuntimeError, match="ADC credentials unavailable"):
            crypto.serialise_rsa_key(key=rsa_key)


def test_writes_rsa_key_to_data_file(crypto, rsa_key, tmp_path, monkeypatch):
    pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    data_path = tmp_path / "data"
    data_path.mkdir()
    monkeypatch.chdir(tmp_path)

    result = crypto.write_rsa_key_to_file("private", pem)

    assert result == data_path / "private.pem"
    assert result.read_bytes() == pem


def test_reads_unencrypted_rsa_private_key_from_file(crypto, rsa_key, tmp_path):
    pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key_path = tmp_path / "private.pem"
    key_path.write_bytes(pem)

    loaded_key = crypto.read_private_rsa_key_from_file(key_path)

    assert loaded_key.private_numbers() == rsa_key.private_numbers()


@pytest.mark.parametrize("password", ["test-password", b"test-password"])
def test_reads_password_protected_rsa_private_key_from_file(
    crypto, rsa_key, tmp_path, password
):
    pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"test-password"),
    )
    key_path = tmp_path / "private.pem"
    key_path.write_bytes(pem)

    loaded_key = crypto.read_private_rsa_key_from_file(key_path, password=password)

    assert loaded_key.private_numbers() == rsa_key.private_numbers()


def test_rejects_non_rsa_private_key_file(crypto, tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key_path = tmp_path / "private.pem"
    key_path.write_bytes(pem)

    with pytest.raises(TypeError, match="does not contain an RSA private key"):
        crypto.read_private_rsa_key_from_file(key_path)


def test_reads_rsa_public_key_from_file(crypto, rsa_key, tmp_path):
    pem = rsa_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_path = tmp_path / "public.pem"
    key_path.write_bytes(pem)

    loaded_key = crypto.read_public_rsa_key_from_file(key_path)

    assert loaded_key.public_numbers() == rsa_key.public_key().public_numbers()


def test_rejects_non_rsa_public_key_file(crypto, tmp_path):
    key = ec.generate_private_key(ec.SECP256R1()).public_key()
    pem = key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_path = tmp_path / "public.pem"
    key_path.write_bytes(pem)

    with pytest.raises(TypeError, match="does not contain an RSA public key"):
        crypto.read_public_rsa_key_from_file(key_path)
