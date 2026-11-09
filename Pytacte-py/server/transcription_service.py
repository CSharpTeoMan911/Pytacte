import queue
import threading
import typing
from collections import deque
from pathlib import Path

import numpy as np
import sherpa_onnx

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

class TrasncriptionResult:
    def __init__(self):
        self.result = ''

class SpeechToTextInterface:
    ASR_FLAG = threading.Event()

    BACKEND = "auto"

    SAMPLE_RATE = 16000

    FRAME_MS = 50

    SPEECH_THRESHOLD = 0.02

    END_SILENCE_MS = 1000
    MIN_SPEECH_MS = 1
    PRE_ROLL_MS = 1000

    """
    stt_models = ['Nemo CTC Critinet 512', 'Nemo CTC Conformer Large', 'Nemo Parakeet TDT-CTC 110M']
    model_precisons = ['Quantised 8', 'Full-Precision 16']
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
                "Full-Precision 32": Path(
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
                "Full-Precision 32": Path(
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

    def __init__(self, model_name:str, model_precision:str):
        MODEL_PATH = Path(self.MODELS[model_name]["precision"][model_precision])


        self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=str(MODEL_PATH),
                tokens=str(Path(self.MODELS[model_name]['path'], 'tokens.txt')),
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
            )


    def add_audio_chunk(self, audio_chunk:bytes | bytearray| memoryview, audio_queue:queue.Queue):
        if isinstance(audio_chunk, (bytes, bytearray, memoryview)):
            samples = np.frombuffer(audio_chunk, dtype=np.float32)
        else:
            samples = np.asarray(audio_chunk, dtype=np.float32)

        samples = np.ascontiguousarray(samples.reshape(-1))

        if samples.size:
            audio_queue.put_nowait(samples)

    def submit_utterance(self, utterance:list, speech_frame_count:int, minimum_frames:int, asr_queue:queue.Queue):
        if speech_frame_count < minimum_frames or not utterance:
            return

        audio = np.concatenate(utterance).astype(np.float32, copy=False)
        asr_queue.put(audio)

    def __asr_worker__(self, asr_queue:queue.Queue, recognition_result:TrasncriptionResult):
        while True:
            audio = asr_queue.get()

            try:
                if audio is None:
                    return

                stream = self.recognizer.create_stream()

                stream.accept_waveform(
                    self.SAMPLE_RATE,
                    audio,
                )

                self.recognizer.decode_stream(stream)

                text = stream.result.text.strip()
                print(text)

                if text:
                    recognition_result.result = text

            finally:
                asr_queue.task_done()

    def __transcription_service__(self, audio_queue:queue.Queue, asr_queue:queue.Queue, recognition_result:TrasncriptionResult):
        silence_limit = max(1, self.END_SILENCE_MS // self.FRAME_MS)
        minimum_frames = max(1, self.MIN_SPEECH_MS // self.FRAME_MS)
        pre_roll_frames = max(1, self.PRE_ROLL_MS // self.FRAME_MS)

        worker = threading.Thread(
            target=self.__asr_worker__,
            daemon=True,
            args=(asr_queue, recognition_result)
        )
        worker.start()

        pre_roll = deque(maxlen=pre_roll_frames)

        utterance = []
        speaking = False
        silence_frames = 0
        speech_frame_count = 0

        try:
            while not self.ASR_FLAG.is_set():
                try:
                    frame = audio_queue.get(timeout=1)
                except queue.Empty:
                    continue

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
                        self.submit_utterance(
                            utterance,
                            speech_frame_count,
                            minimum_frames,
                            asr_queue
                        )

                        speaking = False
                        utterance = []
                        silence_frames = 0
                        speech_frame_count = 0
                        pre_roll.clear()

        finally:
            if speaking and utterance:
                self.submit_utterance(
                    utterance,
                    speech_frame_count,
                    minimum_frames,
                )

            asr_queue.join()
            asr_queue.put(None)

    def start_asr_session(self, audio_queue:queue.Queue, asr_queue:queue.Queue, recognition_result:TrasncriptionResult):
        asr_thread = threading.Thread(
            target=self.__transcription_service__,
            daemon=True,
            name="ASRSession",
            args=(audio_queue, asr_queue, recognition_result)
        )
        asr_thread.start()

    def stop_asr_session(self):
        self.ASR_FLAG.set()
        if self.model is not None:
            self.model.close()
