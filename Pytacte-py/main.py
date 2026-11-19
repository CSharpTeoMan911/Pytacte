import asyncio
import atexit
import os
import queue
import ssl
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from time import monotonic

from websockets.asyncio.server import ServerConnection, serve

from firebase.firebase_auth import FirebaseAuth
from firebase.firebase_database import FirebaseDatabase, ServerAvailabilityDTO
from server.load_balancer import LoadBalancer
from server.transcription_service import SpeechToTextInterface, TrasncriptionResult
from utils.caddy_manager import CaddyManager
from utils.ConfigManager import Config
from utils.Crytography import RSA_Crypto
from utils.IpRateLimiter import RateLimiter

AUTH_CHECKUP_TIME: float = 5  # 5 seconds timeout
FILE_NAME = "server_config.json"

database: FirebaseDatabase | None = None

start_time = 0.0

flag = threading.Event()

thread_pool = ThreadPoolExecutor()

caddy = CaddyManager(thread_pool)

config = Config(encrypt_stream=True)

auth = FirebaseAuth()
ip_rate_limiter = RateLimiter()

loaded_config: object = {}
load_balancer: LoadBalancer | None = None


model_options = {
    "stt_models": {
        "Nemo CTC Critinet 512": {
            "Floating-Point 32": SpeechToTextInterface(
                model_name="Nemo CTC Critinet 512",
                model_precision="Floating-Point 32",
                thread_pool=thread_pool,
            ),
            "Quantised 8": SpeechToTextInterface(
                model_name="Nemo CTC Critinet 512",
                model_precision="Quantised 8",
                thread_pool=thread_pool,
            ),
        },
        "Nemo CTC Conformer Large": {
            "Floating-Point 32": SpeechToTextInterface(
                model_name="Nemo CTC Conformer Large",
                model_precision="Floating-Point 32",
                thread_pool=thread_pool,
            ),
            "Quantised 8": SpeechToTextInterface(
                model_name="Nemo CTC Conformer Large",
                model_precision="Quantised 8",
                thread_pool=thread_pool,
            ),
        },
        "Nemo Parakeet TDT-CTC 110M": {
            "Quantised 8": SpeechToTextInterface(
                model_name="Nemo Parakeet TDT-CTC 110M",
                model_precision="Quantised 8",
                thread_pool=thread_pool,
            ),
        },
    },
    "model_precisions": ["Quantised 8", "Floating-Point 32"],
}


def initiate_config() -> object:
    try:
        result = config.read_config_file(FILE_NAME)

        if not result.successful:
            print(f"--> [ Error: {result.message}]")
            result = config.create_config_file(FILE_NAME)

            if result.successful:
                print(f"--> [{result.message}]")
                return result.payload
        else:
            return result.payload

    except Exception as e:
        print(f"--> [ Error: {e}]")
        raise


def load_balancing(flag: threading.Event):
    global start_time

    prev_time: int = 0
    heartbeat_period: int = 30
    load_balancing_period: int = 60 * 2

    while not flag.is_set():
        current_time = int(monotonic() - start_time)

        if current_time % heartbeat_period == 0 and prev_time != current_time:
            server_id: str = loaded_config["general"]["server_id"]
            server_address = loaded_config["general"]["address"]
            is_load_balancer_node = loaded_config["general"]["is_load_balancer_node"]
            tls = loaded_config["security"]["tls"]

            data = ServerAvailabilityDTO(
                server_id=server_id,
                server_address=server_address,
                load_balancer=is_load_balancer_node,
                tls=tls,
                cpu_usage=0,
            )

            load_balancer.update_cpu_and_ram_metrics(server_id=server_id, data=data)

        if (
            current_time > 0
            and current_time % load_balancing_period == 0
            and prev_time != current_time
            and loaded_config["general"]["is_load_balancer_node"]
        ):
            load_balancer.delete_expired_items()
            load_balancer.sort_servers_by_cpu()

            start_time = monotonic()
            prev_time = 0

        prev_time = current_time


async def cert_management():
    try:
        if loaded_config["security"]["encrypt_stream"]:
            crypto = RSA_Crypto()
            server_cert_path = Path(
                Path.cwd(), "data", loaded_config["security"]["server_cert"]
            )
            private_key = Path(
                Path.cwd(), "data", loaded_config["security"]["private_key"]
            )

            if server_cert_path.exists():
                print("--> [ The server certificate exist. ]")

            elif loaded_config["security"]["generate_self_signed"]:
                private_key = crypto.generate_rsa_key()

                (
                    public_key_bytes,
                    private_key_bytes,
                ) = await crypto.serialise_rsa_key_pair(
                    key=private_key,
                    passwordless=not loaded_config["security"]["encrypt_cert"],
                )

                cert_gen_path: str = await crypto.write_keys_to_cert(
                    loaded_config["security"]["server_cert"],
                    public_key_bytes,
                    private_key_bytes,
                    not loaded_config["security"]["encrypt_cert"],
                )
                private_key_gen_path: str = crypto.write_rsa_key_to_file(
                    loaded_config["security"]["private_key"], private_key_bytes
                )

                print("\n\n--> [[!!!] Generating certificate and private key [!!!]]")
                print(f"--> [Server certificate path: {cert_gen_path}]")
                print(f"--> [Server private key path: {private_key_gen_path}]")
                print("\n\n")
            else:
                raise RuntimeError(
                    "--> [ Error: The public key, private key, or certificate are not available. ]"
                )
    except Exception as e:
        print(f"--> [ Error: {e}]")
        raise


async def transciption_session_heartbeat_manager(
    transcription_id: str, websocket: ServerConnection
):
    is_succcessful, payload = database.update_transcription_job_heartbeat(
        transcription_id=transcription_id
    )

    if not is_succcessful:
        websocket.respond(403, "<Internal_Server_Error/>")
        await websocket.close()


def heartbeat_manager_wrapper(coroutine):
    return asyncio.run(coroutine)


def shutdown():
    if loaded_config["security"]["reverse_proxy"] and caddy.server_pid is not None:
        is_sucessful, message = caddy.shutdown_server()
        if not is_sucessful:
            print(f"--> [ Caddy shutdown error: {message} ]")
    print("--> [ Server shutdown ]")


async def echo(websocket: ServerConnection):

    client_ip: str | None

    transcription_id: str | None

    last_heartbeat = monotonic()

    if not loaded_config["security"]["reverse_proxy"]:
        client_ip = websocket.remote_address[0]
    else:
        forwarded_for = websocket.request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else websocket.remote_address[0]
        )

    if client_ip == None or client_ip == "":
        raise RuntimeError("Invalid client ip address")

    if not ip_rate_limiter.is_allowed(client_ip):
        await websocket.close(code=1013, reason="Rate limit exceeded")
        return

    ASR_FLAG = threading.Event()
    audio_queue = queue.Queue()
    asr_queue = queue.Queue()
    recognition_result: TrasncriptionResult = TrasncriptionResult()

    model: SpeechToTextInterface | None = None

    connection_initiation = time.monotonic()

    jwt_checked: bool = False
    stt_ai_model_paramaters_extracted: bool = False

    try:
        async for message in websocket:
            try:
                stt_model = ""
                model_precision = ""

                auth_label = "<Authorisation_Token>"
                auth_label_end = "</Authorisation_Token>"

                model_label = "<STT_Model>"
                model_label_end = "</STT_Model>"

                model_precision_label = "<STT_Model_Precision>"
                model_precision_label_end = "</STT_Model_Precision>"

                if (
                    not jwt_checked
                    and (time.monotonic() - connection_initiation) >= AUTH_CHECKUP_TIME
                ):
                    websocket.respond(403, "<Invalid_Message/>")
                    await websocket.close()
                    return

                if not jwt_checked and isinstance(message, str):
                    if auth_label in message and auth_label_end in message:
                        jwt_token = ""
                        token_begin = message.index(auth_label) + len(auth_label)
                        token_end = message.index(auth_label_end)

                        for i in range(token_begin, token_end):
                            jwt_token += message[i]

                        jwt_valid, jwt_validation_message = auth.validate_id_token(
                            jwt_token
                        )

                        if not jwt_valid:
                            match jwt_validation_message:
                                case "Invalid token":
                                    await websocket.send(
                                        message="<JWT_Invalid/>", text=True
                                    )
                                case "Expired token":
                                    await websocket.send(
                                        message="<JWT_Token_Expired/>", text=True
                                    )
                                case "Token revoked":
                                    await websocket.send(
                                        message="<JWT_Token_Revoked/>", text=True
                                    )
                                case "User disabled":
                                    await websocket.send(
                                        message="<Invalid_Account/>", text=True
                                    )
                                case "Certificate error":
                                    await websocket.send(
                                        message="<Internal_Server_Error/>", text=True
                                    )

                        else:
                            if (
                                isinstance(jwt_validation_message, object)
                                and database is not None
                            ):
                                uid = jwt_validation_message["uid"]
                                server_id = loaded_config["general"]["server_id"]

                                if jwt_validation_message["uid"]:
                                    [is_successful, payload] = (
                                        database.create_transcription_job(
                                            user_uid=uid, server_id=server_id
                                        )
                                    )

                                    if not is_successful:
                                        if (
                                            "User has reached the maximum number of transcription jobs "
                                            in payload
                                        ):
                                            await websocket.send(
                                                message="<Max_Transcriptions_Limit_Reached/>",
                                                text=True,
                                            )
                                        else:
                                            await websocket.send(
                                                message="<Internal_Server_Error/>",
                                                text=True,
                                            )
                                    else:
                                        if isinstance(payload.transcription_id, str):
                                            transcription_id = payload.transcription_id

                                            await websocket.send(
                                                message="<JWT_Valid/>", text=True
                                            )

                                            jwt_checked = True
                                        else:
                                            await websocket.send(
                                                message="<Internal_Server_Error/>",
                                                text=True,
                                            )

                            else:
                                await websocket.send(
                                    message="<Internal_Server_Error/>",
                                    text=True,
                                )

                elif not stt_ai_model_paramaters_extracted and isinstance(message, str):
                    if model_label in message and model_label_end in message:
                        stt_model_begin = message.index(model_label) + len(model_label)
                        stt_model_end = message.index(model_label_end)

                        for i in range(stt_model_begin, stt_model_end):
                            stt_model += message[i]

                        model_precision_begin = message.index(
                            model_precision_label
                        ) + len(model_precision_label)
                        model_precision_end = message.index(model_precision_label_end)

                        for i in range(model_precision_begin, model_precision_end):
                            model_precision += message[i]

                        if (
                            stt_model in model_options["stt_models"]
                            and model_precision in model_options["model_precisions"]
                            and model_precision
                            in model_options["stt_models"][stt_model]
                        ):
                            if model is None:
                                model = model_options["stt_models"][stt_model][
                                    model_precision
                                ]
                                model.start_asr_session(
                                    audio_queue=audio_queue,
                                    asr_queue=asr_queue,
                                    recognition_result=recognition_result,
                                    thread_flag=ASR_FLAG,
                                )

                                await websocket.send(
                                    message="<Valid_Model_Parameters/>", text=True
                                )
                                stt_ai_model_paramaters_extracted = True
                            else:
                                await websocket.send(
                                    message="<Invalid_Model_Parameters/>", text=True
                                )
                                await websocket.close()

                        else:
                            await websocket.send(
                                message="<Invalid_Model_Parameters/>", text=True
                            )
                            await websocket.close()

                else:
                    elapsed = monotonic() - last_heartbeat

                    if (
                        isinstance(message, bytes)
                        and isinstance(model, SpeechToTextInterface)
                        and database is not None
                    ):
                        if elapsed > 60:
                            thread_pool.submit(
                                heartbeat_manager_wrapper,
                                transciption_session_heartbeat_manager(
                                    transcription_id=transcription_id,
                                    websocket=websocket,
                                ),
                            )
                            last_heartbeat = monotonic()

                        model.add_audio_chunk(
                            audio_chunk=message, audio_queue=audio_queue
                        )
                        recognition_result.result = recognition_result.result.strip()
                        if recognition_result.result != "":
                            await websocket.send(
                                message=recognition_result.result, text=True
                            )
                        recognition_result.result = ""
                    else:
                        websocket.respond(403, "<Invalid_Message/>")
                        await websocket.close()

            except ValueError as ve:
                print(f"--> [ Error: {ve} ]")

    except Exception as e:  # noqa: BLE001, F841, S110
        print(e)

    except KeyboardInterrupt:
        ASR_FLAG.set()

    finally:
        ASR_FLAG.set()


async def main():
    try:
        global load_balancer
        global loaded_config
        global start_time
        global database

        atexit.register(shutdown)

        print("--> [ Loading server configuration ]")

        loaded_config = initiate_config()

        print("--> [ Loading server certificates ]")
        await cert_management()

        print("--> [ Initiating the Firebase Admin SDK app ]")

        await auth.initiate_app(loaded_config["firebase"]["firebase_key_name"])

        print("--> [ Firebase Admin SDK app initiated ]")

        print("--> [ Initalising load balancer ]")

        database_url = loaded_config["general"]["database_url"]
        max_transcription_jobs = loaded_config["transcription"][
            "max_transcription_jobs_per_user"
        ]

        server_id = loaded_config["general"]["server_id"]
        server_address = loaded_config["general"]["address"]
        is_load_balancer_node = loaded_config["general"]["is_load_balancer_node"]
        tls = loaded_config["security"]["tls"]

        data = ServerAvailabilityDTO(
            server_id=server_id,
            server_address=server_address,
            load_balancer=is_load_balancer_node,
            tls=tls,
            cpu_usage=0,
        )
        load_balancer = LoadBalancer(
            database_url=database_url,
            max_transcription_jobs_per_user=max_transcription_jobs,
            firebase_app=auth.get_app(),
        )
        is_successful, message = load_balancer.update_cpu_and_ram_metrics(
            server_id=server_id, data=data
        )

        if not is_successful:
            raise ValueError(
                f"( Please add a valid firebase database url ) ( {message} )"
            )
        else:
            print("--> [ Load balancer initialised ]")

        print("--> [ Initialising database ]")

        database = FirebaseDatabase(
            database_url=database_url,
            max_transcription_jobs_per_user=max_transcription_jobs,
            firebase_app=auth.get_app(),
        )

        print("--> [ Database initialised ]")

        if loaded_config["security"]["reverse_proxy"]:
            is_dev: bool = loaded_config["caddy_reverse_proxy"]["is_dev"]

            print("--> [ Loading caddy reverse proxy ]")
            is_sucessful, message = caddy.download_for_current_platform()

            if is_sucessful:
                is_sucessful, message = caddy.set_config(is_dev)

                if not is_sucessful:
                    raise ValueError(f"Caddy configuration error: {message}")

                is_sucessful, message = caddy.start_server()
                if not is_sucessful:
                    raise ValueError(f"Caddy startup error: {message}")

            else:
                raise ValueError(f"Caddy download error: {message}")

        start_time = monotonic()
        thread_pool.submit(load_balancing, flag=flag)

        IP = loaded_config["general"]["ip_address"]
        PORT = loaded_config["general"]["port_number"]

        if (
            loaded_config["security"]["encrypt_stream"]
            and not loaded_config["security"]["reverse_proxy"]
        ):
            crypto = RSA_Crypto()
            private_cert_path = Path(
                Path.cwd(), "data", loaded_config["security"]["server_cert"]
            )
            private_key_path = Path(
                Path.cwd(), "data", loaded_config["security"]["private_key"]
            )
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

            try:
                ssl_context.load_cert_chain(
                    certfile=private_cert_path, keyfile=private_key_path
                )
            except Exception as e:  # noqa: BLE001
                print(
                    f"--> [ Error: {e}]",
                    "--> [ Extracting the private key password . . . ]",
                )
                ssl_context.load_cert_chain(
                    certfile=private_cert_path,
                    keyfile=private_key_path,
                    password=await crypto.get_private_key_password(),
                )

            print("\n\n--> [ Server initiated - (encrypted) ]")
            print(f"--> [ Server listening on IP: {IP}, PORT: {PORT} ]")

            server = await serve(echo, IP, PORT, ssl=ssl_context)
            await server.serve_forever()
        else:
            print("\n\n--> [ Server initiated - (unencrypted) ]")
            print(f"--> [ Server listening on IP: {IP}, PORT: {PORT} ]")

            server = await serve(echo, IP, PORT)
            await server.serve_forever()

    except Exception as e:
        print(f"--> [Error: {e}]")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        flag.set()
        os.close(0)
