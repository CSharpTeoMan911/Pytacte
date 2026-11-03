import { useEffect, useRef } from 'react';

type Props = {
  stream: MediaStream | null;
};

export default function LiveWaveformVisualiser({ stream }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !stream) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    const audioContext = new AudioContext();
    void audioContext.resume();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024 * 16;
    source.connect(analyser);

    const samples = new Uint8Array(analyser.fftSize);
    let animationFrame = 0;

    const resizeCanvas = () => {
      const { width, height } = canvas.getBoundingClientRect();
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(width * pixelRatio));
      canvas.height = Math.max(1, Math.floor(height * pixelRatio));
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    };

    const resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(canvas);
    resizeCanvas();

    const draw = () => {
      const { width, height } = canvas.getBoundingClientRect();
      analyser.getByteTimeDomainData(samples);
      context.clearRect(0, 0, width, height);
      context.beginPath();
      context.lineWidth = 2;
      context.strokeStyle = '#f8f8f8';

      for (let i = 0; i < samples.length; i += 1) {
        const x = (i / (samples.length - 1)) * width;
        const y = (samples[i] / 255) * height;
        if (i === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      }

      context.stroke();
      animationFrame = window.requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      source.disconnect();
      void audioContext.close();
    };
  }, [stream]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Live microphone waveform"
      style={{ display: 'block', width: '100%', height: '100%', minWidth: 0 }}
    />
  );
}
