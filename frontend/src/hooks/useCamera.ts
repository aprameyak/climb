import { useCallback, useRef, useState } from 'react';

interface UseCameraReturn {
  stream: MediaStream | null;
  capturedImages: string[];
  isCapturing: boolean;
  error: string | null;
  videoRef: React.RefObject<HTMLVideoElement>;
  startCamera: (facingMode?: 'environment' | 'user') => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
  clearCaptures: () => void;
  removeCapture: (index: number) => void;
}

export function useCamera(): UseCameraReturn {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedImages, setCapturedImages] = useState<string[]>([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const startCamera = useCallback(
    async (facingMode: 'environment' | 'user' = 'environment') => {
      setError(null);
      try {
        if (stream) {
          stream.getTracks().forEach((t) => t.stop());
        }

        const constraints: MediaStreamConstraints = {
          video: {
            facingMode,
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
        };

        const newStream = await navigator.mediaDevices.getUserMedia(constraints);
        setStream(newStream);
        setIsCapturing(true);

        if (videoRef.current) {
          videoRef.current.srcObject = newStream;
          await videoRef.current.play();
        }
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : 'Camera access denied or unavailable';
        setError(msg);
      }
    },
    [stream]
  );

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCapturing(false);
  }, [stream]);

  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current) return null;

    const video = videoRef.current;
    if (video.readyState !== video.HAVE_ENOUGH_DATA) return null;

    // Create/reuse canvas
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas');
    }
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);

    setCapturedImages((prev) => [...prev, dataUrl]);
    return dataUrl;
  }, []);

  const clearCaptures = useCallback(() => {
    setCapturedImages([]);
  }, []);

  const removeCapture = useCallback((index: number) => {
    setCapturedImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  return {
    stream,
    capturedImages,
    isCapturing,
    error,
    videoRef,
    startCamera,
    stopCamera,
    captureFrame,
    clearCaptures,
    removeCapture,
  };
}
