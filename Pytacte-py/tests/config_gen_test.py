import json

from utils.ConfigManager import Config, ConfigResult


def make_config():
    return Config(
        ip_address="127.0.0.1",
        port_number=8080,
        address="127.0.0.1:8080",
        encrypt_stream=True,
        tls=False,
        encrypt_cert=True,
        generate_self_signed=True,
        server_cert="server.pem",
        private_key="private.pem",
        max_transcription_jobs_per_user=5,
        reverse_proxy=True,
        is_load_balancer_node=False,
        database_url="https://example.firebaseio.com",
        server_id="server-test",
        is_dev=False,
    )


def expected_config():
    return {
        "general": {
            "ip_address": "127.0.0.1",
            "port_number": 8080,
            "address": "127.0.0.1:8080",
            "is_load_balancer_node": False,
            "database_url": "https://example.firebaseio.com",
            "server_id": "server-test",
        },
        "security": {
            "encrypt_stream": True,
            "tls": False,
            "encrypt_cert": True,
            "generate_self_signed": True,
            "server_cert": "server.pem",
            "private_key": "private.pem",
            "reverse_proxy": True,
        },
        "transcription": {"max_transcription_jobs_per_user": 5},
        "firebase": {"firebase_key_name": "KEY_NAME"},
        "caddy_reverse_proxy": {"is_dev": False},
    }


def test_config_result_stores_result_fields():
    payload = {"status": "ok"}

    result = ConfigResult(True, "Configuration generation successful", payload)

    assert result.successful is True
    assert result.message == "Configuration generation successful"
    assert result.payload is payload


def test_config_stores_named_configuration_values():
    config = make_config()

    assert config.config == expected_config()


def test_create_config_file_writes_json_configuration(tmp_path):
    config = make_config()
    config_path = tmp_path / "config.json"

    result = config.create_config_file(config_path)

    assert result.successful is True
    assert result.message == "Configuration generation successful"
    assert result.payload == expected_config()
    assert json.loads(config_path.read_text(encoding="utf-8")) == expected_config()


def test_create_config_file_returns_failure_for_invalid_path(tmp_path):
    config = make_config()
    invalid_path = tmp_path / "missing" / "config.json"

    result = config.create_config_file(invalid_path)

    assert result.successful is False
    assert result.payload is None
    assert result.message


def test_read_config_file_returns_file_contents(tmp_path):
    config = make_config()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(expected_config()), encoding="utf-8")

    result = config.read_config_file(config_path)

    assert result.successful is True
    assert result.message == "Configuration extraction successful"
    assert result.payload == expected_config()


def test_read_config_file_returns_failure_for_missing_file(tmp_path):
    config = make_config()

    result = config.read_config_file(tmp_path / "missing.json")

    assert result.successful is False
    assert result.payload is None
    assert result.message
