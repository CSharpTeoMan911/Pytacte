let mediaRecorder: MediaRecorder | undefined;
let mediaStream: MediaStream | undefined;

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
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = async(event) => {
                if (event.data.size === 0) return;
                const bytes:ArrayBuffer = await event.data.arrayBuffer();

                streamAudioCallback(bytes);
            };
            mediaRecorder.start(10);
            


            return ['Media device initialised', true];
        }
        else {
            return ['No audio device detected', true];
        }
    }
    catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        console.error('Unable to start audio capture:', errorMessage);
        return [errorMessage, false];
    }
}

export function StopAudioCapture(): [string, boolean] {
    try {
        //mediaRecorder?.removeEventListener('dataavailable', eventListener, true);
        mediaRecorder?.stop();
        mediaStream?.getTracks().forEach((track) => track.stop());

        mediaRecorder = undefined;
        mediaStream = undefined;

        return['Media device capture stopped', true]
    }
    catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        console.error('Unable to start audio capture:', errorMessage);
        return [errorMessage, false];
    }
}
