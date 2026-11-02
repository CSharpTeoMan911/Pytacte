import { useEffect, useRef, useState } from 'react';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import WaveSurfer from 'wavesurfer.js';

type Props = {
    onDataAvailable?: (event: BlobEvent) => void;
};

export default function LiveWaveformRecorder({ onDataAvailable }: Props) {
    const waveformRef = useRef<HTMLDivElement | null>(null);
    const waveSurferRef = useRef<WaveSurfer | null>(null);
    //const recordPluginRef = useRef<ReturnType<typeof RecordPlugin.create> | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const micRendererRef = useRef<{ onDestroy: () => void } | null>(null);

    const [isRecording, setIsRecording] = useState(false);
    const [isStarting, setIsStarting] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        if (!waveformRef.current) return;

        const waveSurfer = WaveSurfer.create({
            container: waveformRef.current,
            waveColor: '#4ba2f8',
            progressColor: '#158fd6',
            cursorWidth: 0,
            height: 80,
            barWidth: 2,
            barGap: 2,
            interact: false,
        });

        /*
        const recordPlugin = RecordPlugin.create({
            renderRecordedAudio: false,
            scrollingWaveform: true,
            scrollingWaveformWindow: 5,
            mediaRecorderTimeslice: 250,
        });

        waveSurfer.registerPlugin(recordPlugin);
        waveSurferRef.current = waveSurfer;
        recordPluginRef.current = recordPlugin;
        */

        return () => {
            mediaRecorderRef.current?.stop();
            streamRef.current?.getTracks().forEach((track) => track.stop());
            micRendererRef.current?.onDestroy();
            waveSurfer.destroy();
        };
    }, []);

    const stopRecording = () => {
        mediaRecorderRef.current?.stop();
        mediaRecorderRef.current = null;
        micRendererRef.current?.onDestroy();
        micRendererRef.current = null;
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setIsRecording(false);
    };

    const startRecording = async () => {
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
            setErrorMessage('Microphone recording is not supported by this browser.');
            return;
        }

        setIsStarting(true);
        setErrorMessage('');

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    onDataAvailable?.(event);
                }
            };

            //micRendererRef.current = recordPluginRef.current?.renderMicStream(stream) ?? null;
            streamRef.current = stream;
            mediaRecorderRef.current = mediaRecorder;
            mediaRecorder.start(250);
            setIsRecording(true);
        } catch (error) {
            streamRef.current?.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
            setErrorMessage(error instanceof DOMException && error.name === 'NotAllowedError'
                ? 'Microphone permission was denied.'
                : 'Unable to access the microphone.');
        } finally {
            setIsStarting(false);
        }
    };

    const handleToggle = () => {
        if (isRecording) {
            stopRecording();
        } else {
            void startRecording();
        }
    };

    return (
        <div>
            <div ref={waveformRef} aria-label="Live microphone waveform" />
            <IconButton
                onClick={handleToggle}
                disabled={isStarting}
                aria-label={isRecording ? 'Stop microphone recording' : 'Start microphone recording'}
                sx={{ color: '#158fd6' }}
            >
                {isRecording ? <MicOffIcon /> : <MicIcon />}
            </IconButton>
            {errorMessage && (
                <Typography color="error" variant="body2">
                    {errorMessage}
                </Typography>
            )}
        </div>
    );
}
