import json
import os
from pathlib import Path


class ConfigResult:
    def __init__(self, successful, message, payload):
        self.successful = successful
        self.message = message
        self.payload = payload
        
class Config:
    def __init__(self, ip_address:str = '127.0.0.1', port_number:int = 80, use_gcloud:bool = False, use_encryption:bool = False, socket_backlog:int=100, max_transcription_jobs_per_user:int=10):
        self.config = {
            'ip_address':ip_address,
            'port_number':port_number,
            'use_gcloud':use_gcloud,
            'use_encryption':use_encryption,
            'socket_backlog':socket_backlog,
            'max_transcription_jobs_per_user':max_transcription_jobs_per_user
        }
        
    def __delete_config_file__(self, file_name):
        path = Path(Path.cwd(), 'data', file_name)
        os.remove(path=path)
        
    def create_config_file(self, file_name:str) -> ConfigResult:
        try:
            path = Path(Path.cwd(), 'data', file_name)
            
            if path.exists():
                self.__delete_config_file__()
            
            with open(path, 'wb') as fw:
                fw.write(json.dumps(self.config, indent=4).encode('utf-8'))
                fw.flush()
                return ConfigResult(True, 'Configuration generation successful', self.config)
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), self.config)
    
    def read_config_file(self, file_name) -> ConfigResult:
        try:
            path = Path(Path.cwd(), 'data', file_name)
            
            with open(path, 'rb') as fr:
                file = fr.read()
                return ConfigResult(True, 'Configuration extraction successful', json.loads(file))
        except Exception as e:  # noqa: BLE001
            return ConfigResult(False, str(e), None)
    