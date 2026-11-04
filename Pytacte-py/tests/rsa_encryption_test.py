import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


UTILS_PATH = Path(__file__).resolve().parents[1] / "utils"
if str(UTILS_PATH) not in sys.path:
    sys.path.insert(0, str(UTILS_PATH))

import Crytography
from Crytography import Crypto


@pytest.fixture
def crypto():
    return Crypto()


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


def test_serialises_password_protected_rsa_key(crypto):
    key = crypto.generate_rsa_key()
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
        pem = crypto.serialise_rsa_key(
            passwordless=False,
            key=key,
        )

    loaded_key = serialization.load_pem_private_key(
        pem,
        password=b"test-password",
    )
    assert isinstance(loaded_key, rsa.RSAPrivateKey)
    assert loaded_key.private_numbers() == key.private_numbers()


def test_serialises_unencrypted_rsa_key_when_passwordless(crypto):
    key = crypto.generate_rsa_key()
    auth_result = Mock(successful=True)

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        secrets_manager.return_value.verifyGoogleCloudAuthentication.return_value = (
            auth_result
        )
        pem = crypto.serialise_rsa_key(passwordless=True, key=key)

    loaded_key = serialization.load_pem_private_key(pem, password=None)
    assert isinstance(loaded_key, rsa.RSAPrivateKey)
    assert loaded_key.private_numbers() == key.private_numbers()


def test_rejects_serialisation_when_google_authentication_fails(crypto):
    key = crypto.generate_rsa_key()
    auth_result = Mock(
        successful=False,
        message="ADC credentials unavailable",
    )

    with patch.object(Crytography, "GoogleSecretsManager") as secrets_manager:
        secrets_manager.return_value.verifyGoogleCloudAuthentication.return_value = (
            auth_result
        )

        with pytest.raises(RuntimeError, match="ADC credentials unavailable"):
            crypto.serialise_rsa_key(key=key)


def test_writes_rsa_key_to_data_file(crypto, tmp_path, monkeypatch):
    key = crypto.generate_rsa_key()
    pem = key.private_bytes(
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


def test_reads_unencrypted_rsa_key_from_file(crypto, tmp_path):
    key = crypto.generate_rsa_key()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    key_path = tmp_path / "private.pem"
    key_path.write_bytes(pem)

    loaded_key = crypto.read_rsa_key_from_file(key_path)

    assert loaded_key.private_numbers() == key.private_numbers()


def test_reads_password_protected_rsa_key_from_file(crypto, tmp_path):
    key = crypto.generate_rsa_key()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"test-password"),
    )
    key_path = tmp_path / "private.pem"
    key_path.write_bytes(pem)

    loaded_key = crypto.read_rsa_key_from_file(key_path, password="test-password")

    assert loaded_key.private_numbers() == key.private_numbers()
