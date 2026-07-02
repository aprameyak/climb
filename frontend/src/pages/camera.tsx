import type { NextPage } from 'next';
import { useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { PageLayout } from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useCamera } from '@/hooks/useCamera';
import { useCreateAnalysis } from '@/hooks/useAnalysis';
import { useAppStore } from '@/store/useAppStore';
import { AlertTriangle, Camera, FlipHorizontal, Image, Trash2, Upload, X } from 'lucide-react';
import { useState } from 'react';

const CameraPage: NextPage = () => {
  const router = useRouter();
  const {
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
  } = useCamera();

  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const { mutate: createAnalysis, isPending } = useCreateAnalysis();
  const { isAnalyzing, currentProfile } = useAppStore();

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const handleFlip = async () => {
    const newMode = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(newMode);
    await startCamera(newMode);
  };

  const handleAnalyze = () => {
    if (capturedImages.length === 0) return;

    // Convert data URLs to File objects
    const files = capturedImages.map((dataUrl, i) => {
      const arr = dataUrl.split(',');
      const mime = arr[0].match(/:(.*?);/)?.[1] ?? 'image/jpeg';
      const bstr = atob(arr[1]);
      const n = bstr.length;
      const u8arr = new Uint8Array(n);
      for (let j = 0; j < n; j++) u8arr[j] = bstr.charCodeAt(j);
      return new File([u8arr], `capture_${i + 1}.jpg`, { type: mime });
    });

    createAnalysis(
      { files, profileId: currentProfile?.id },
      { onSuccess: (result) => router.push(`/analysis/${result.id}`) }
    );
  };

  return (
    <PageLayout title="Camera Capture" maxWidth="2xl">
      <div className="space-y-4">
        {/* Camera feed */}
        <Card>
          <div className="relative bg-slate-900 rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              className="w-full h-full object-cover"
            />
            {!isCapturing && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <Camera size={48} className="mx-auto text-slate-600 mb-2" />
                  <p className="text-sm text-slate-500">Camera not started</p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-start gap-2 mt-3 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <div className="flex gap-2 mt-3">
            {!isCapturing ? (
              <Button
                onClick={() => startCamera(facingMode)}
                leftIcon={<Camera size={16} />}
                className="flex-1"
              >
                Start Camera
              </Button>
            ) : (
              <>
                <Button
                  onClick={captureFrame}
                  leftIcon={<Image size={16} />}
                  className="flex-1"
                >
                  Capture
                </Button>
                <Button
                  onClick={handleFlip}
                  variant="secondary"
                  leftIcon={<FlipHorizontal size={16} />}
                >
                  Flip
                </Button>
                <Button
                  onClick={stopCamera}
                  variant="ghost"
                >
                  Stop
                </Button>
              </>
            )}
          </div>
        </Card>

        {/* Captured images */}
        {capturedImages.length > 0 && (
          <Card
            header={
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200">
                  Captured Frames ({capturedImages.length})
                </span>
                <button
                  onClick={clearCaptures}
                  className="text-xs text-slate-500 hover:text-red-400 flex items-center gap-1"
                >
                  <Trash2 size={12} />
                  Clear all
                </button>
              </div>
            }
          >
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {capturedImages.map((img, i) => (
                <div key={i} className="relative group rounded-lg overflow-hidden border border-slate-700">
                  <img src={img} alt={`Capture ${i + 1}`} className="w-full h-20 object-cover" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors" />
                  <button
                    onClick={() => removeCapture(i)}
                    className="absolute top-1 right-1 bg-slate-900/80 rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
                  >
                    <X size={12} className="text-white" />
                  </button>
                  <div className="absolute bottom-1 left-1 text-xs text-white/60 bg-black/40 rounded px-1">
                    #{i + 1}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3">
              <Button
                onClick={handleAnalyze}
                disabled={capturedImages.length === 0}
                loading={isPending || isAnalyzing}
                leftIcon={<Upload size={16} />}
                size="lg"
                className="w-full"
              >
                Analyze {capturedImages.length} frame{capturedImages.length !== 1 ? 's' : ''}
              </Button>
            </div>
          </Card>
        )}

        {/* Tips */}
        <Card>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Tips for best results</h3>
          <ul className="space-y-1 text-xs text-slate-500">
            <li>• Capture the entire wall section with all holds visible</li>
            <li>• Take photos from directly in front of the wall (not angled)</li>
            <li>• Include the start holds and finish hold in the same shot</li>
            <li>• Multiple angles improve hold detection accuracy</li>
            <li>• Good lighting helps — avoid harsh shadows across holds</li>
          </ul>
        </Card>
      </div>
    </PageLayout>
  );
};

export default CameraPage;
