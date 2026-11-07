import asyncio
import logging
import os
import ssl
import time
from pathlib import Path

from websockets.asyncio.server import ServerConnection, serve

from server.transcription_service import SpeechToTextInterface
from utils.ConfigManager import Config
from utils.Crytography import RSA_Crypto

AUTH_CHECKUP_TIME:float = 5 # 5 seconds timeout
FILE_NAME = 'server_config.json'

config = Config(use_encryption=True)

loaded_config:object = {}

stt_models = ['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']
model_precisons = ['Quantised 8', 'Full-Precision 16']

active_interfaces = []


def on_shutdown():
    for interface in tuple(active_interfaces):
        interface.dispose()
    active_interfaces.clear()


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

async def echo(websocket: ServerConnection) -> None:
    model: SpeechToTextInterface | None = None
    connection_initiation = time.monotonic()
    jwt_checked = False
    model_parameters_extracted = False

    auth_label = '<Authorisation_Token>'
    auth_label_end = '</Authorisation_Token>'
    model_label = '<STT_Model>'
    model_label_end = '</STT_Model>'
    precision_label = '<STT_Model_Precision>'
    precision_label_end = '</STT_Model_Precision>'

    try:
        async for message in websocket:
            if not jwt_checked:
                if time.monotonic() - connection_initiation >= AUTH_CHECKUP_TIME:
                    await websocket.close(code=1008, reason='Authentication timed out')
                    return

                if (
                    isinstance(message, str)
                    and auth_label in message
                    and auth_label_end in message
                ):
                    jwt_token = message.split(auth_label, 1)[1].split(auth_label_end, 1)[0]
                    # Mock validation
                    jwt_valid = True
                    if jwt_valid:
                        await websocket.send('<JWT_Valid/>', text=True)
                        jwt_checked = True
                    else:
                        await websocket.send('<JWT_Invalid/>', text=True)
                        await websocket.close(code=1008, reason='Invalid token')
                        return
                continue

            if not model_parameters_extracted:
                if not isinstance(message, str):
                    continue
                if (
                    model_label not in message
                    or model_label_end not in message
                    or precision_label not in message
                    or precision_label_end not in message
                ):
                    continue

                stt_model = message.split(model_label, 1)[1].split(model_label_end, 1)[0]
                model_precision = message.split(precision_label, 1)[1].split(
                    precision_label_end, 1
                )[0]

                if stt_model not in stt_models or model_precision not in model_precisons:
                    await websocket.send('<Invalid_Model_Parameters/>', text=True)
                    await websocket.close(code=1008, reason='Invalid model selection')
                    return

                model = SpeechToTextInterface(
                    model_name=stt_model,
                    precision=model_precision,
                )
                active_interfaces.append(model)
                model.stt_session()
                model_parameters_extracted = True
                await websocket.send('<Valid_Model_Parameters/>', text=True)
                continue

            if isinstance(message, bytes) and model is not None:
                model.add_audio_chunk(message)
                await websocket.send(model.get_transcription(), text=True)

    finally:
        if model is not None:
            if model in active_interfaces:
                active_interfaces.remove(model)
            await asyncio.to_thread(model.dispose)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )
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
    finally:
        on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        os.close(0)
