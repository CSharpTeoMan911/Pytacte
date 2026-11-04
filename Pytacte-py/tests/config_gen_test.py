import json

from utils.ConfigManager import Config, ConfigResult


def test_config_result_stores_result_fields():
    payload = {"status": "ok"}

    result = ConfigResult(True, "Configuration generation successful", payload)

    assert result.successful is True
    assert result.message == "Configuration generation successful"
    assert result.payload is payload


def test_config_stores_named_configuration_values():
    config = Config("127.0.0.1", 8080, True, False)

    assert config.config == {
        "ip_address": "127.0.0.1",
        "port_number": 8080,
        "use_gcloud": True,
        "use_encryption": False,
    }


def test_create_config_file_writes_json_configuration(tmp_path):
    config = Config("127.0.0.1", 8080, True, False)
    config_path = tmp_path / "config.json"

    result = config.create_config_file(config_path)

    assert result.successful is True
    assert result.message == "Configuration generation successful"
    assert result.payload is None
    assert json.loads(config_path.read_text(encoding="utf-8")) == config.config


def test_create_config_file_returns_failure_for_invalid_path(tmp_path):
    config = Config("127.0.0.1", 8080, True, False)
    invalid_path = tmp_path / "missing" / "config.json"

    result = config.create_config_file(invalid_path)

    assert result.successful is False
    assert result.payload is None
    assert result.message


def test_read_config_file_returns_file_contents(tmp_path):
    config = Config("127.0.0.1", 8080, True, False)
    config_path = tmp_path / "config.json"
    expected_contents = b'{"use_gcloud": true}'
    config_path.write_bytes(expected_contents)

    result = config.read_config_file(config_path)

    assert result.successful is True
    assert result.message == "Configuration extraction successful"
    assert result.payload == expected_contents


def test_read_config_file_returns_failure_for_missing_file(tmp_path):
    config = Config("127.0.0.1", 8080, True, False)

    result = config.read_config_file(tmp_path / "missing.json")

    assert result.successful is False
    assert result.payload is None
    assert result.message
