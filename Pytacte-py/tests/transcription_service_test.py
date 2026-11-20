import queue
import threading
import wave
from concurrent.futures import ThreadPoolExecutor

from server.transcription_service import SpeechToTextInterface


def test_transcription_service_with_helloworld_wav():
    shutdown_flag = threading.Event()
    session_flag = threading.Event()
    results_queue = queue.Queue()
    audio_queue = queue.Queue()
    asr_queue = queue.Queue()
    executor = ThreadPoolExecutor(max_workers=3)
    service = None

    try:
        service = SpeechToTextInterface(
            model_name="Nemo CTC Critinet 512",
            model_precision="Quantised 8",
            thread_pool=executor,
            shutdown_flag=shutdown_flag,
        )
        service.start_asr_session(
            audio_queue=audio_queue,
            asr_queue=asr_queue,
            results_queue=results_queue,
            thread_flag=session_flag,
            uid="test-session",
        )

        with wave.open("HelloWorld.wav", "rb") as wav_file:
            assert wav_file.getnchannels() == 1
            assert wav_file.getsampwidth() == 4
            assert wav_file.getframerate() == service.SAMPLE_RATE

            while samples := wav_file.readframes(800):
                service.add_audio_chunk(samples, audio_queue)

        silence = b"\x00" * (800 * 4)
        for _ in range(service.END_SILENCE_MS // service.FRAME_MS):
            service.add_audio_chunk(silence, audio_queue)

        transcription = results_queue.get(timeout=30).strip().lower()

        assert transcription
        assert "hello" in transcription or "world" in transcription
        assert audio_queue.unfinished_tasks == 0
        assert asr_queue.unfinished_tasks == 0
    finally:
        session_flag.set()
        shutdown_flag.set()
        if service is not None:
            with service._batch_condition:
                service._batch_condition.notify_all()
        executor.shutdown(wait=True)
