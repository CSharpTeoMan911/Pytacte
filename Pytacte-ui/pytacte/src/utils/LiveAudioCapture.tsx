import { Microphone } from 'decibri';

let mediaStream: MediaStream | undefined;
let mic: Microphone | undefined;

export async function StartLiveAudioCapture(
    streamAudioCallback: (bytes: ArrayBuffer) => void,
    onStreamReady: (stream: MediaStream) => void,
): Promise<[string, boolean]> {
    try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const stream = await navigator.mediaDevices
                .getUserMedia(
                    // constraints - only audio needed for this app
                    {
                        audio: true,
                    },
                );

            mediaStream = stream;
            onStreamReady(stream);

            // Float32 - native browser format, no conversion
            mic = new Microphone({sampleRate:16000, dtype: 'float32', channels:1 });
            mic.on('data', (chunk:Buffer<ArrayBufferLike>) => {
                streamAudioCallback(chunk.buffer as ArrayBuffer)
            });
            (mic as unknown as { start: () => void }).start();

            return ['Media device initialised', true];
        }
        else {
            return ['No audio device detected', true];
        }
    }
    catch (e) {
        console.log(e)
        const errorMessage = e instanceof Error ? e.message : String(e);
        console.error('Unable to start audio capture:', errorMessage);
        return [errorMessage, false];
    }
}

export function StopAudioCapture(): [string, boolean] {
    try {
        //mediaRecorder?.removeEventListener('dataavailable', eventListener, true);
        mic?.stop();

        mic = undefined;
        mediaStream = undefined;

        return ['Media device capture stopped', true]
    }
    catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        console.error('Unable to start audio capture:', errorMessage);
        return [errorMessage, false];
    }
}
