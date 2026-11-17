import json
import os
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
        audio_stream_byte_rate_per_second:int = 80000,
        database_url:str = "REPLACE_WITH_FIREBASE_YOUR_DATABASE_URL",
        server_id:str = "server_1"
    ):
        self.config = {
            "general": {
                "ip_address": ip_address,
                "port_number": port_number,
                "address":address,
                "is_load_balancer_node": is_load_balancer_node,
                "audio_stream_byte_rate_per_second":audio_stream_byte_rate_per_second,
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
        }

    def __delete_config_file__(self, file_name):
        path = Path(Path.cwd(), "data", file_name)
        os.remove(path=path)

    def create_config_file(self, file_name: str) -> ConfigResult:
        try:
            path = Path(Path.cwd(), "data", file_name)

            if path.exists():
                self.__delete_config_file__()

            with open(path, "wb") as fw:
                fw.write(json.dumps(self.config, indent=4).encode("utf-8"))
                fw.flush()
                return ConfigResult(
                    True, "Configuration generation successful", self.config
                )
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), self.config)

    def read_config_file(self, file_name) -> ConfigResult:
        try:
            path = Path(Path.cwd(), "data", file_name)

            with open(path, "rb") as fr:
                file = fr.read()
                return ConfigResult(
                    True, "Configuration extraction successful", json.loads(file)
                )
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), None)
