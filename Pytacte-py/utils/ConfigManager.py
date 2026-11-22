import json
from pathlib import Path


class ConfigResult:
    def __init__(self, successful, message, payload):
        self.successful = successful
        self.message = message
        self.payload = payload


class Config:
    def __init__(
        self,
        ip_address: str = "127.0.0.1",
        port_number: int = 80,
        address: str = '127.0.0.1:80',
        encrypt_stream: bool = True,
        tls:bool = True,
        encrypt_cert: bool = False,
        generate_self_signed: bool = False,
        server_cert: str = "server_cert.pem",
        private_key: str = "private_key.pem",
        max_transcription_jobs_per_user: int = 10,
        reverse_proxy:bool = False,
        is_load_balancer_node:bool = True,
        database_url:str = "REPLACE_WITH_FIREBASE_YOUR_DATABASE_URL",
        server_id:str = "server_1",
        is_dev:bool = True
    ):
        self.config = {
            "general": {
                "ip_address": ip_address,
                "port_number": port_number,
                "address":address,
                "is_load_balancer_node": is_load_balancer_node,
                "database_url":database_url,
                "server_id":server_id
            },
            "security": {
                "encrypt_stream": encrypt_stream,
                "tls": tls,
                "encrypt_cert": encrypt_cert,
                "generate_self_signed": generate_self_signed,
                "server_cert": server_cert,
                "private_key": private_key,
                "reverse_proxy": reverse_proxy
            },
            "transcription": {
                "max_transcription_jobs_per_user": max_transcription_jobs_per_user,
            },
            "firebase": {
                "firebase_key_name":'KEY_NAME'
            },
            "caddy_reverse_proxy":{
                "is_dev":is_dev
            }
        }

    @staticmethod
    def _config_path(file_name: str | Path) -> Path:
        path = Path(file_name)
        if path.is_absolute():
            return path
        return Path.cwd() / "data" / path

    def create_config_file(self, file_name: str | Path) -> ConfigResult:
        try:
            path = self._config_path(file_name)
            path.write_text(
                json.dumps(self.config, indent=4),
                encoding="utf-8",
            )
            return ConfigResult(
                True, "Configuration generation successful", self.config
            )
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), None)

    def read_config_file(self, file_name: str | Path) -> ConfigResult:
        try:
            path = self._config_path(file_name)
            return ConfigResult(
                True,
                "Configuration extraction successful",
                json.loads(path.read_text(encoding="utf-8")),
            )
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), None)
