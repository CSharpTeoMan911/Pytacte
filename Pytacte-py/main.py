import asyncio
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa
from websockets.asyncio.server import serve

from utils.ConfigManager import Config
from utils.Crytography import RSA_Crypto

FILE_NAME = 'server_config.json'

config = Config(use_encryption=True)

loaded_config:object = {}
private_key:rsa.RSAPrivateKey | None = None
public_key:rsa.RSAPublicKey | None = None

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
    
async def cert_management():
    try:
        if loaded_config['use_encryption']:
            global public_key, private_key
            
            crypto = RSA_Crypto()
            public_cert_path = Path(Path.cwd(), 'data', loaded_config['public_key'])
            private_cert_path = Path(Path.cwd(), 'data', loaded_config['private_key'])
            
            if public_cert_path.exists() and private_cert_path.exists():
                private_key = await crypto.read_private_rsa_key_from_file(private_cert_path)
                public_key = crypto.read_public_rsa_key_from_file(public_cert_path)
                    
            elif loaded_config['generate_self_signed']:
                private_key = crypto.generate_rsa_key()
                public_key = private_key.public_key()
                
                public_key_bytes, private_key_bytes = await crypto.serialise_rsa_key_pair(key=private_key, passwordless=not loaded_config['encrypt_private_cert'])
                
                private_key_gen_path:str = crypto.write_rsa_key_to_file(private_cert_path, private_key_bytes)
                public_key_gen_path:str = crypto.write_rsa_key_to_file(public_cert_path, public_key_bytes)
                
                print('\n\n--> [[!!!] Generating public and private keys [!!!]]')
                print(f'--> [Public key path: {public_key_gen_path}]')
                print(f'--> [Public key path: {private_key_gen_path}]')
                print('\n\n')
            else:
                raise RuntimeError('--> [ Error: The public and/or private key is not available. ]')
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
        global loaded_config
        loaded_config = initiate_config()
        await cert_management()
        
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
