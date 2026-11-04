import asyncio
from unittest.mock import AsyncMock, Mock, patch

from utils.GoogleSecretsManager import GoogleSecretsManager


def run_async(coroutine):
    return asyncio.run(coroutine)


def test_get_secret_returns_secret_payload():
    manager = GoogleSecretsManager()
    client = Mock()
    payload = object()

    with (
        patch.object(manager, "__createSecretManager__", return_value=client),
        patch.object(
            manager, "__getSecret__", new=AsyncMock(return_value=payload)
        ) as get_secret,
    ):
        result = run_async(manager.getSecret("app-secret"))

    assert result.message == "Secret retrieval successful"
    assert result.successful is True
    assert result.payload is payload
    get_secret.assert_awaited_once_with("app-secret", client)


def test_get_secret_converts_runtime_error_to_return_value():
    manager = GoogleSecretsManager()
    error = RuntimeError("ADC credentials unavailable")

    with patch.object(manager, "__createSecretManager__", side_effect=error):
        result = run_async(manager.getSecret("app-secret"))

    assert result.message == str(error)
    assert result.successful is False
    assert result.payload is None


def test_set_secret_creates_secret_and_adds_version():
    manager = GoogleSecretsManager()
    client = Mock()
    created_secret = object()
    secret_version = object()

    with (
        patch.object(manager, "__createSecretManager__", return_value=client),
        patch.object(
            manager, "__setSecret__", new=AsyncMock(return_value=created_secret)
        ) as set_secret,
        patch.object(
            manager,
            "__setSecretVersion__",
            new=AsyncMock(return_value=secret_version),
        ) as set_secret_version,
    ):
        result = run_async(manager.setSecret("app-secret", "secret-value"))

    assert result.message == "Secret addition successful"
    assert result.successful is True
    assert result.payload is secret_version
    set_secret.assert_awaited_once_with("app-secret", "secret-value", client)
    set_secret_version.assert_awaited_once_with(
        "app-secret", "secret-value", client
    )


def test_set_secret_adds_version_when_secret_already_exists():
    manager = GoogleSecretsManager()
    client = Mock()
    secret_version = object()

    with (
        patch.object(
            manager,
            "__createSecretManager__",
            side_effect=[client, client],
        ),
        patch.object(
            manager,
            "__setSecret__",
            new=AsyncMock(side_effect=RuntimeError("Secret already exists")),
        ),
        patch.object(
            manager,
            "__setSecretVersion__",
            new=AsyncMock(return_value=secret_version),
        ) as set_secret_version,
    ):
        result = run_async(manager.setSecret("app-secret", "secret-value"))

    assert result.message == "Secret addition successful"
    assert result.successful is True
    assert result.payload is secret_version
    set_secret_version.assert_awaited_once_with(
        "app-secret", "secret-value", client
    )


def test_set_secret_returns_runtime_error():
    manager = GoogleSecretsManager()
    error = RuntimeError("Credential refresh failed")

    with patch.object(manager, "__createSecretManager__", side_effect=error):
        result = run_async(manager.setSecret("app-secret", "secret-value"))

    assert result.message == str(error)
    assert result.successful is False
    assert result.payload is None
