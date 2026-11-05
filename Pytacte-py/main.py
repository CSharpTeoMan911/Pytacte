import asyncio
import os
import ssl
from pathlib import Path

from websockets.asyncio.server import serve

from utils.ConfigManager import Config
from utils.Crytography import RSA_Crypto

FILE_NAME = 'server_config.json'

config = Config(use_encryption=True)

loaded_config:object = {}

def initiate_config() -> object:
    try:
        result = config.read_config_file(FILE_NAME)
        
        if not result.successful:
            print(f'--> [ Error: {result.message}]')
            result = config.create_config_file(FILE_NAME)
            
            if result.successful:
                print(f'--> [{result.message}]')
                return result.payload
        else:
            return result.payload
                
    except Exception as e:
        print(f'--> [ Error: {e}]')
        raise
    
async def cert_management():
    try:
        if loaded_config['use_encryption']:
            
            crypto = RSA_Crypto()
            server_cert_path = Path(Path.cwd(), 'data', loaded_config['server_cert'])
            private_key = Path(Path.cwd(), 'data', loaded_config['private_key'])
            
            if server_cert_path.exists():
                print('--> [ The server certificate exist. ]')
                    
            elif loaded_config['generate_self_signed']:
                private_key = crypto.generate_rsa_key()
                
                public_key_bytes, private_key_bytes = await crypto.serialise_rsa_key_pair(key=private_key, passwordless=not loaded_config['encrypt_cert'])
                
                cert_gen_path:str = await crypto.write_keys_to_cert(loaded_config['server_cert'], public_key_bytes, private_key_bytes, not loaded_config['encrypt_cert'])
                private_key_gen_path:str = crypto.write_rsa_key_to_file(loaded_config['private_key'], private_key_bytes)
                
                print('\n\n--> [[!!!] Generating certificate and private key [!!!]]')
                print(f'--> [Server certificate path: {cert_gen_path}]')
                print(f'--> [Server private key path: {private_key_gen_path}]')
                print('\n\n')
            else:
                raise RuntimeError('--> [ Error: The public key, private key, or certificate are not available. ]')
    except Exception as e:
        print(f'--> [ Error: {e}]')
        raise

async def echo(websocket):
    print(loaded_config)
    initiated:bool = False
    async for message in websocket:
        response = ''
        if message == '[ Client request: (use_encryption)]' and not initiated:
            response = f'[ Server response: (use_encryption == {loaded_config['use_encryption']})]'
        else:
            response = 'Mock message'
            
        await websocket.send(response)

async def main():
    try:
        print('--> [ Loading server configuration ]')
        global loaded_config
        loaded_config = initiate_config()
        
        print('--> [ Loading server certificates ]')
        await cert_management()
        
        IP = loaded_config['ip_address']
        PORT = loaded_config['port_number']
        
        if loaded_config['use_encryption']:
            crypto = RSA_Crypto()
            private_cert_path = Path(Path.cwd(), 'data', loaded_config['server_cert'])
            private_key_path = Path(Path.cwd(), 'data', loaded_config['private_key'])
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            try:
                ssl_context.load_cert_chain(certfile=private_cert_path, keyfile=private_key_path)
            except Exception as e:  # noqa: BLE001
                print(f'--> [ Error: {e}]', '--> [ Extracting the private key password . . . ]')
                ssl_context.load_cert_chain(certfile=private_cert_path, keyfile=private_key_path, password= await crypto.get_private_key_password())
            
            print('\n\n--> [ Server initiated ]')
            print(f'--> [ Server listening on IP: {IP}, PORT: {PORT} ]')
            
            server = await serve(echo, IP, PORT, ssl=ssl_context)
            await server.serve_forever()
        else:
            print('\n\n--> [ Server initiated ]')
            print(f'--> [ Server listening on IP: {IP}, PORT: {PORT} ]')
            
            server = await serve(echo, IP, PORT)
            await server.serve_forever()
        
        
    except Exception as e:
        print(f'--> [Error: {e}]')
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        os.close(0)
