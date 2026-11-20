import queue
import shutil
import tarfile
import tempfile
import threading
import typing
import urllib.request
from collections import deque
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import sherpa_onnx
from sherpa_onnx import OfflineStream

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------



class SpeechToTextInterface:
    BACKEND = "auto"

    SAMPLE_RATE = 16000

    FRAME_MS = 50

    SPEECH_THRESHOLD = 0.02

    END_SILENCE_MS = 1000
    MIN_SPEECH_MS = 1
    PRE_ROLL_MS = 1000

    """
    stt_models = ['Nemo CTC Critinet 512', 'Nemo CTC Conformer Large', 'Nemo Parakeet TDT-CTC 110M']
    model_precisons = ['Quantised 8', 'Floating-Point 32']
    """
    model: sherpa_onnx.OfflineRecognizer | None = None

    MODELS: typing.ClassVar = {
        "Nemo CTC Critinet 512": {
            "path": Path(
                Path.cwd(),
                "data",
                "models",
                "sherpa-onnx-nemo-ctc-en-citrinet-512",
            ),
            "precision": {
                "Floating-Point 32": Path(
                    Path.cwd(),
                    "data",
                    "models",
                    "sherpa-onnx-nemo-ctc-en-citrinet-512",
                    "model.onnx",
                ),
                "Quantised 8": Path(
                    Path.cwd(),
                    "data",
                    "models",
                    "sherpa-onnx-nemo-ctc-en-citrinet-512",
                    "model.int8.onnx",
                ),
            },
        },
        "Nemo CTC Conformer Large": {
            "path": Path(
                Path.cwd(),
                "data",
                "models",
                "sherpa-onnx-nemo-ctc-en-conformer-large",
            ),
            "precision": {
                "Floating-Point 32": Path(
                    Path.cwd(),
                    "data",
                    "models",
                    "sherpa-onnx-nemo-ctc-en-conformer-large",
                    "model.onnx",
                ),
                "Quantised 8": Path(
                    Path.cwd(),
                    "data",
                    "models",
                    "sherpa-onnx-nemo-ctc-en-conformer-large",
                    "model.int8.onnx",
                ),
            },
        },
        "Nemo Parakeet TDT-CTC 110M": {
            "path": Path(
                Path.cwd(),
                "data",
                "models",
                "sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8",
            ),
            "precision": {
                "Quantised 8": Path(
                    Path.cwd(),
                    "data",
                    "models",
                    "sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8",
                    "model.int8.onnx",
                ),
            },
        },
    }

    MODEL_URLS: typing.ClassVar = {
        "Nemo CTC Critinet 512": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-ctc-en-citrinet-512.tar.bz2",
        "Nemo CTC Conformer Large": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-ctc-en-conformer-large.tar.bz2",
        "Nemo Parakeet TDT-CTC 110M": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8.tar.bz2",
    }

    def __init__(
        self, model_name: str, model_precision: str, thread_pool: ThreadPoolExecutor, shutdown_flag: threading.Event
    ):
        MODEL_PATH = Path(self.MODELS[model_name]["precision"][model_precision])
        if not MODEL_PATH.exists():
            print(f"\n\n--> [ Downloading model: ({model_name}) ]")
            self.__download_model__(model_name)
            print(f"--> [ Downloaded model: ({model_name}) ]\n\n")

        self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
            model=str(MODEL_PATH),
            tokens=str(Path(self.MODELS[model_name]["path"], "tokens.txt")),
            num_threads=2,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
        )
        self.thread_pool = thread_pool
        self.session_batches: dict[str, tuple[list[OfflineStream], queue.Queue]] = {}
        self._batch_condition = threading.Condition()

        self.thread_pool.submit(self.__inference_worker__, shutdown_flag)


    def __download_model__(self, model_name: str):
        """Download and unpack the selected model under ``data/models``."""
        model_url = self.MODEL_URLS[model_name]
        model_directory = Path(self.MODELS[model_name]["path"])
        models_directory = model_directory.parent
        models_directory.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=models_directory) as temp_directory:
            archive_path = Path(temp_directory, "model.tar.bz2")
            with urllib.request.urlopen(model_url) as response, archive_path.open("wb") as archive_file:
                shutil.copyfileobj(response, archive_file)

            with tarfile.open(archive_path, "r:bz2") as archive:
                destination = models_directory.resolve()
                members = archive.getmembers()

                # Reject links and paths outside the models directory before
                # extracting any archive contents.
                for member in members:
                    member_path = (models_directory / member.name).resolve()
                    if (
                        not member_path.is_relative_to(destination)
                        or member.issym()
                        or member.islnk()
                        or not (member.isfile() or member.isdir())
                    ):
                        raise ValueError(f"Unsafe model archive member: {member.name}")

                archive.extractall(models_directory, members=members)

        if not model_directory.is_dir():
            raise FileNotFoundError(
                f"Downloaded model archive did not contain {model_directory.name}"
            )

    def add_audio_chunk(
        self, audio_chunk: bytes | bytearray | memoryview, audio_queue: queue.Queue
    ):
        if isinstance(audio_chunk, (bytes, bytearray, memoryview)):
            samples = np.frombuffer(audio_chunk, dtype=np.float32)
        else:
            samples = np.asarray(audio_chunk, dtype=np.float32)

        samples = np.ascontiguousarray(samples.reshape(-1))

        if samples.size:
            audio_queue.put_nowait(samples)

    def __submit_utterance__(
        self,
        utterance: list,
        speech_frame_count: int,
        minimum_frames: int,
        asr_queue: queue.Queue,
    ):
        if speech_frame_count < minimum_frames or not utterance:
            return

        audio = np.concatenate(utterance).astype(np.float32, copy=False)
        asr_queue.put(audio)

    def __inference_worker__(self, flag:threading.Event):
        while True:
            with self._batch_condition:
                while not flag.is_set() and not self.session_batches:
                    self._batch_condition.wait(timeout=0.1)

                if flag.is_set() and not self.session_batches:
                    return

                pending_batches = list(self.session_batches.values())
                self.session_batches.clear()

            streams: list[OfflineStream] = []
            stream_results: list[queue.Queue] = []
            for sessions, results in pending_batches:
                streams.extend(sessions)
                stream_results.extend([results] * len(sessions))

            if not streams:
                continue
        
            for stream in streams:
                self.recognizer.decode_stream(stream)
                text = stream.result.text.strip()
                if text:
                    results.put(text)

    def __asr_worker__(
        self,
        asr_queue: queue.Queue,
        results_queue: queue.Queue,
        thread_flag: threading.Event,
        uid:str
    ):
        while not thread_flag.is_set():
            audio = asr_queue.get()

            try:
                if audio is None:
                    return

                stream = self.recognizer.create_stream()

                stream.accept_waveform(
                    self.SAMPLE_RATE,
                    audio,
                )

                with self._batch_condition:
                    batch = self.session_batches.get(uid)
                    if batch is None:
                        sessions = []
                        batch = (sessions, results_queue)
                        self.session_batches[uid] = batch
                    else:
                        sessions, _ = batch

                    sessions.append(stream)
                    self._batch_condition.notify()

            finally:
                asr_queue.task_done()

    def __transcription_service__(
        self,
        audio_queue: queue.Queue,
        asr_queue: queue.Queue,
        results_queue: queue.Queue,
        thread_flag: threading.Event,
        uid:str
    ):
        silence_limit = max(1, self.END_SILENCE_MS // self.FRAME_MS)
        minimum_frames = max(1, self.MIN_SPEECH_MS // self.FRAME_MS)
        pre_roll_frames = max(1, self.PRE_ROLL_MS // self.FRAME_MS)

        self.thread_pool.submit(
            self.__asr_worker__,
            asr_queue=asr_queue,
            results_queue=results_queue,
            thread_flag=thread_flag,
            uid=uid
        )

        pre_roll = deque(maxlen=pre_roll_frames)

        utterance = []
        speaking = False
        silence_frames = 0
        speech_frame_count = 0

        try:
            while not thread_flag.is_set():
                try:
                    frame = audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

                try:
                    if frame.size == 0:
                        continue

                    rms = float(np.sqrt(np.mean(np.square(frame))))
                    is_speech = rms >= self.SPEECH_THRESHOLD

                    if not speaking:
                        pre_roll.append(frame)

                        if is_speech:
                            speaking = True
                            utterance = list(pre_roll)
                            pre_roll.clear()

                            silence_frames = 0
                            speech_frame_count = 1

                    else:
                        utterance.append(frame)

                        if is_speech:
                            silence_frames = 0
                            speech_frame_count += 1
                        else:
                            silence_frames += 1

                        if silence_frames >= silence_limit:
                            self.__submit_utterance__(
                                utterance=utterance,
                                speech_frame_count=speech_frame_count,
                                minimum_frames=minimum_frames,
                                asr_queue=asr_queue,
                            )

                            speaking = False
                            utterance = []
                            silence_frames = 0
                            speech_frame_count = 0
                            pre_roll.clear()
                finally:
                    audio_queue.task_done()

        finally:
            if speaking and utterance:
                self.__submit_utterance__(
                    utterance=utterance,
                    speech_frame_count=speech_frame_count,
                    minimum_frames=minimum_frames,
                    asr_queue=asr_queue,
                )

            asr_queue.join()
            asr_queue.put(None)

    def start_asr_session(
        self,
        uid:str,
        audio_queue: queue.Queue,
        asr_queue: queue.Queue,
        results_queue: queue.Queue,
        thread_flag: threading.Event,
    ):

        self.thread_pool.submit(
            self.__transcription_service__,
            audio_queue=audio_queue,
            asr_queue=asr_queue,
            results_queue= results_queue,
            thread_flag=thread_flag,
            uid=uid
        )

