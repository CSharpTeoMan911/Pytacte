import queue
import threading
import typing
from collections import deque
from pathlib import Path

import numpy as np
import transcribe_cpp

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------


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
    stt_models = ['Moonshine Streaming Medium', 'Granite Speech 5.0 TurboCTC', 'Parakeet TDT-CTC 110M']
    model_precisons = ['Quantised 8', 'Full-Precision 16']
    """
    model: transcribe_cpp.Model | None = None

    MODELS: typing.ClassVar = {
        "Moonshine Streaming Medium": {
            "Full-Precision 16": Path(
                "data",
                "models",
                "moonshine-streaming-medium-gguf",
                "moonshine-streaming-medium-F16.gguf",
            ),
            "Quantised 8": Path(
                "data",
                "models",
                "moonshine-streaming-medium-gguf",
                "moonshine-streaming-medium-Q8_0.gguf",
            ),
        },
        "Granite Speech 5.0 TurboCTC": {
            "Full-Precision 16": Path(
                "data",
                "models",
                "granite-speech-5.0-470m-turboctc-gguf",
                "granite-speech-5.0-470m-turboctc-FP16.gguf",
            ),
            "Quantised 8": Path(
                "data",
                "models",
                "granite-speech-5.0-470m-turboctc-gguf",
                "granite-speech-5.0-470m-turboctc-Q8.gguf",
            ),
        },
        "Parakeet TDT-CTC 110M": {
            "Full-Precision 16": Path(
                "data",
                "models",
                "parakeet-tdt_ctc-110m-gguf",
                "parakeet-tdt_ctc-110m-F16.gguf",
            ),
            "Quantised 8": Path(
                "data",
                "models",
                "parakeet-tdt_ctc-110m-gguf",
                "parakeet-tdt_ctc-110m-Q8_0.gguf",
            ),
        },
    }

    def __init__(self, model_name, model_precision):
        MODEL_PATH = self.MODELS[model_name][model_precision]
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
            return

        self.model = transcribe_cpp.Model(path=MODEL_PATH, backend=self.BACKEND)

        self.audio_queue = queue.Queue()
        self.asr_queue = queue.Queue()

    def log_callback(level, message):
        try:
            pass
        except Exception as e:  # noqa: BLE001, F841, S110
            pass

    def add_audio_chunk(self, audio_chunk):
        """Convert an audio chunk to a flat float32 array and queue it."""
        try:
            if isinstance(audio_chunk, (bytes, bytearray, memoryview)):
                samples = np.frombuffer(audio_chunk, dtype=np.float32)
            else:
                samples = np.asarray(audio_chunk, dtype=np.float32)

            samples = np.ascontiguousarray(samples.reshape(-1), dtype=np.float32)
            if samples.size > 0:
                self.audio_queue.put_nowait(samples)

        except Exception as e:  # noqa: BLE001, F841, S110
            pass

    def submit_utterance(self, utterance, speech_frame_count, minimum_frames):
        try:
            if speech_frame_count < minimum_frames or not utterance:
                return

            audio = np.concatenate(utterance).astype(
                np.float32,
                copy=False,
            )

            self.asr_queue.put(audio)

        except Exception as e:  # noqa: BLE001, F841, S110
            pass
        
    # ------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------


    def __asr_worker__(self, session):
        while True:
            try:
                audio = self.asr_queue.get()
            except Exception as e:  # noqa: BLE001, F841, S112
                continue

            try:
                if audio is None:
                    return

                audio = np.ascontiguousarray(audio, dtype=np.float32)

                result = session.run(audio)
                text = result.text.strip()

                if text:
                    print(f"[Result: {text}]", flush=True)

            except Exception as e:  # noqa: BLE001, F841, S110
                pass

            finally:
                self.asr_queue.task_done()

    def __transcription_service__(self):
        try:
            silence_limit = max(1, self.END_SILENCE_MS // self.FRAME_MS)
            minimum_frames = max(1, self.MIN_SPEECH_MS // self.FRAME_MS)
            pre_roll_frames = max(1, self.PRE_ROLL_MS // self.FRAME_MS)

            with self.model, self.model.session() as session:
                worker = threading.Thread(
                    target=self.__asr_worker__,
                    args=(session,),
                    daemon=True,
                    name="ASRWorker",
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
                            frame = self.audio_queue.get(block=True, timeout=1)

                        except queue.Empty:
                            continue

                        except Exception as e:  # noqa: BLE001, F841, S112
                            continue

                        try:  #################################################
                            #               [ RMS FORMULA ]
                            #################################################
                            #             __________________________
                            #            /
                            #           /               N
                            #          /              -----
                            #         /       1       \
                            #        /       ---  *    >    (X)i ^2
                            #  _    /         N       /
                            #   \  /                  -----
                            #    \/                    i=1
                            #
                            #################################################

                            # Calculate RMS using every sample.
                            N = len(frame)
                            _sum = sum([float(n * n) for n in frame])

                            rms = float(np.sqrt(float(1 / N) * _sum))

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
                                    )

                                    speaking = False
                                    utterance = []
                                    silence_frames = 0
                                    speech_frame_count = 0
                                    pre_roll.clear()

                        except Exception as e:  # noqa: BLE001, F841, S110
                            pass

                except KeyboardInterrupt:
                    pass

                except Exception as e:  # noqa: BLE001, F841, S110
                    pass

                finally:
                    try:
                        if speaking and utterance:
                            self.submit_utterance(
                                utterance,
                                speech_frame_count,
                                minimum_frames,
                            )
                    except Exception as e:  # noqa: BLE001, F841, S110
                        pass

                    try:
                        self.asr_queue.join()
                    except Exception as e:  # noqa: BLE001, F841, S110
                        pass

                    try:
                        self.asr_queue.put(None)
                        worker.join()
                    except Exception as e:  # noqa: BLE001, F841, S110
                        pass

        except KeyboardInterrupt:
            pass

        except Exception as e:  # noqa: BLE001, F841, S110
            pass

    def start_asr_session(self):
        asr_thread = threading.Thread(
            target=self.__transcription_service__,
            daemon=True,
            name="ASRSession",
        )
        asr_thread.start()
        
    def stop_asr_session(self):
        self.ASR_FLAG.set()
        if self.model is not None:
            self.model.close()
        
