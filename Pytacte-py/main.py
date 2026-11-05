import asyncio
import os
import socket
import threading

from websockets.asyncio.server import serve

from utils.ConfigManager import Config

FILE_NAME = 'server_config.json'
config = Config(use_encryption=True, use_gcloud=True)

global loaded_config
loaded_config = {}

def initiate_config() -> object:
    try:
        result = config.read_config_file(FILE_NAME)
        
        if not result.successful:
            print(f'--> [{result.message}]')
            result = config.create_config_file(FILE_NAME)
            
            if result.successful:
                print(f'--> [{result.message}]')
                return result.payload
        else:
            return result.payload
                
    except Exception as e:
        print(f'--> [Error: {e}]')
        raise

async def echo(websocket):
    initiated:bool = False
    async for message in websocket:
        loaded_config = initiate_config()
        response = ''
        if message == '[ Client request: (use_encryption)]' and not initiated:
            response = f'[ Server response: (use_encryption == {loaded_config['use_encryption']})]'
        else:
            response = 'Mock message'
            
        await websocket.send(response)

async def main():
    try:
        loaded_config = initiate_config()
        
        print(loaded_config)
        
        IP = loaded_config['ip_address']
        PORT = loaded_config['port_number']
        
        server = await serve(echo, IP, PORT)
        await server.serve_forever()
        
    except Exception as e:
        print(f'--> [Error: {e}]')
        raise

if __name__ == "__main__":
    asyncio.run(main())