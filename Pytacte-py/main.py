import asyncio
import os
import socket
import threading

from websockets.asyncio.server import serve

from utils.ConfigManager import Config

FILE_NAME = 'server_config.json'
config = Config(use_encryption=True, use_gcloud=True)

def create_config():
    try:
        result = config.create_config_file(FILE_NAME)
        
        if result.successful:
            print(f'--> [{result.message}]')
            result = config.read_config_file(FILE_NAME)
            
            if result.successful:
                print(f'--> [{result.message}]')
                
    except Exception as e:  # noqa: BLE001
         print(f'--> [{e}]')

async def echo(websocket):
    async for message in websocket:
        print(message)
        await websocket.send(message)

async def main():
    try:
        IP = config.config['ip_address']
        PORT = config.config['port_number']
        
        server = await serve(echo, IP, PORT)
        await server.serve_forever()
        
    except Exception as e:  # noqa: BLE001
        print(f'--> [{e}]')
        

if __name__ == "__main__":
    asyncio.run(main())