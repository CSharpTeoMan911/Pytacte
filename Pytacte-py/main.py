import asyncio
import os
import ssl
import time
from pathlib import Path

from websockets.asyncio.server import ServerConnection, serve

from utils.ConfigManager import Config
from utils.Crytography import RSA_Crypto

AUTH_CHECKUP_TIME:float = 5 # 5 seconds timeout
FILE_NAME = 'server_config.json'

config = Config(use_encryption=True)

loaded_config:object = {}

stt_models = ['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']
model_precisons = ['Quantised 8', 'Full-Precision 16']


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
        if loaded_config['security']['use_encryption']:
            
            crypto = RSA_Crypto()
            server_cert_path = Path(Path.cwd(), 'data', loaded_config['security']['server_cert'])
            private_key = Path(Path.cwd(), 'data', loaded_config['security']['private_key'])
            
            if server_cert_path.exists():
                print('--> [ The server certificate exist. ]')
                    
            elif loaded_config['security']['generate_self_signed']:
                private_key = crypto.generate_rsa_key()
                
                public_key_bytes, private_key_bytes = await crypto.serialise_rsa_key_pair(key=private_key, passwordless=not loaded_config['security']['encrypt_cert'])
                
                cert_gen_path:str = await crypto.write_keys_to_cert(loaded_config['security']['server_cert'], public_key_bytes, private_key_bytes, not loaded_config['security']['encrypt_cert'])
                private_key_gen_path:str = crypto.write_rsa_key_to_file(loaded_config['security']['private_key'], private_key_bytes)
                
                print('\n\n--> [[!!!] Generating certificate and private key [!!!]]')
                print(f'--> [Server certificate path: {cert_gen_path}]')
                print(f'--> [Server private key path: {private_key_gen_path}]')
                print('\n\n')
            else:
                raise RuntimeError('--> [ Error: The public key, private key, or certificate are not available. ]')
    except Exception as e:
        print(f'--> [ Error: {e}]')
        raise

async def echo(websocket:ServerConnection):
    client_ip = websocket.remote_address[0]
    
    '''
    TODO: Implement rate limiter
    ________________________________
    
    # RATE LIMITER CALL
    
    
    if limit_reached:
        websocket.close()
    '''
    
    
    
    connection_initiation = time.monotonic()
    
    jwt_checked:bool = False 
    stt_ai_model_paramaters_extracted:bool = False
    
    async for message in websocket:
        try:
            print(f'--> Message: {message}\n\n')
            stt_model = ''
            model_precision = ''
            
            auth_label = '<Authorisation_Token>'
            auth_label_end = '</Authorisation_Token>'
            
            model_label = '<STT_Model>'
            model_label_end = '</STT_Model>'
            
            model_precision_label = '<STT_Model_Precision>'
            model_precision_label_end = '</STT_Model_Precision>'
                
            
            if not jwt_checked and (time.monotonic() - connection_initiation) >= AUTH_CHECKUP_TIME:
                websocket.respond(403, '<Invalid_Message/>')
                websocket.close()
                return
            
            
            if not jwt_checked and isinstance(message, str):                
                if auth_label in message and auth_label_end in message:
                    jwt_token = ''
                    token_begin = message.index(auth_label) + len(auth_label)
                    token_end =  message.index(auth_label_end)
                    
                    for i in range(token_begin, token_end):
                        jwt_token += message[i]
                    
                    # Mock validation
                    jwt_valid = True # Mock value
                    
                    if jwt_valid:
                        await websocket.send(message='<JWT_Valid/>', text=True)
                        jwt_checked = True
                    else:
                        await websocket.send(message='<JWT_Invalid/>', text=True)
                        await websocket.close()
                        
            elif not stt_ai_model_paramaters_extracted and isinstance(message, str):
                print(f'--> Model parameters: {message}')
                if model_label in message and model_label_end in message:
                    stt_model_begin = message.index(model_label) + len(model_label)
                    stt_model_end =  message.index(model_label_end)
                    
                    for i in range(stt_model_begin, stt_model_end):
                        stt_model += message[i]
                    
                    model_precision_begin = message.index(model_precision_label) + len(model_precision_label)
                    model_precision_end =  message.index(model_precision_label_end)
                    
                    for i in range(model_precision_begin, model_precision_end):
                        model_precision += message[i]
                    
                    
                    print(f'STT Model: {stt_model}')
                    print(f'Model precision: {model_precision}\n\n')
                    
                    if stt_models.count(stt_model) > 0 and model_precisons.count(model_precision) > 0:
                        await websocket.send(message='<Valid_Model_Parameters/>', text=True)
                        stt_ai_model_paramaters_extracted = True
                    else:
                        await websocket.send(message='<Invalid_Model_Parameters/>', text=True)
                        await websocket.close()
        
            else:
                if isinstance(message, bytes):
                    print(message)
            
        except ValueError as ve:
            print(f'--> [ Error: {ve} ]')
        

async def main():
    try:
        print('--> [ Loading server configuration ]')
        global loaded_config
        loaded_config = initiate_config()
        
        print('--> [ Loading server certificates ]')
        await cert_management()
        
        IP = loaded_config['general']['address']
        PORT = loaded_config['general']['port_number']
        
        if loaded_config['security']['use_encryption']:
            crypto = RSA_Crypto()
            private_cert_path = Path(Path.cwd(), 'data', loaded_config['security']['server_cert'])
            private_key_path = Path(Path.cwd(), 'data', loaded_config['security']['private_key'])
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            try:
                ssl_context.load_cert_chain(certfile=private_cert_path, keyfile=private_key_path)
            except Exception as e:  # noqa: BLE001
                print(f'--> [ Error: {e}]', '--> [ Extracting the private key password . . . ]')
                ssl_context.load_cert_chain(certfile=private_cert_path, keyfile=private_key_path, password= await crypto.get_private_key_password())
            
            print('\n\n--> [ Server initiated - (encrypted) ]')
            print(f'--> [ Server listening on IP: {IP}, PORT: {PORT} ]')
            
            server = await serve(echo, IP, PORT, ssl=ssl_context)
            await server.serve_forever()
        else:
            print('\n\n--> [ Server initiated - (unencrypted) ]')
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
