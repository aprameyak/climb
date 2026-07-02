import type { NextPage } from 'next';
import { useState } from 'react';
import { useRouter } from 'next/router';
import { PageLayout } from '@/components/layout/PageLayout';
import { ImageUpload } from '@/components/ImageUpload';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useCreateAnalysis } from '@/hooks/useAnalysis';
import { useProfiles } from '@/hooks/useProfile';
import { useAppStore } from '@/store/useAppStore';
import { AlertTriangle, CheckCircle, Upload } from 'lucide-react';

const BOARD_TYPES = [
  { value: 'unknown', label: 'Unknown / Gym Wall' },
  { value: 'moonboard', label: 'MoonBoard' },
  { value: 'kilter', label: 'Kilter Board' },
  { value: 'tension', label: 'Tension Board' },
  { value: 'spray', label: 'Spray Wall' },
  { value: 'gym', label: 'Gym (colored tape)' },
];

const BETA_TYPE_OPTIONS = [
  { value: 'high_percentage', label: 'High Percentage (recommended)' },
  { value: 'energy_efficient', label: 'Energy Efficient' },
  { value: 'static', label: 'Static Only' },
  { value: 'dynamic', label: 'Dynamic' },
  { value: 'shortest', label: 'Fewest Moves' },
  { value: 'low_power', label: 'Low Power' },
];

const ImportPage: NextPage = () => {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [boardType, setBoardType] = useState('unknown');
  const [selectedBetaTypes, setSelectedBetaTypes] = useState(['high_percentage', 'energy_efficient']);
  const [notes, setNotes] = useState('');

  const { currentProfile } = useAppStore();
  const { data: profiles } = useProfiles();
  const [selectedProfileId, setSelectedProfileId] = useState<string>(currentProfile?.id ?? '');

  const { mutate: createAnalysis, isPending, error, isSuccess } = useCreateAnalysis();
  const { isAnalyzing, analysisProgress } = useAppStore();

  const handleAnalyze = () => {
    if (files.length === 0) return;
    createAnalysis(
      {
        files,
        profileId: selectedProfileId || undefined,
        boardType,
        betaTypes: selectedBetaTypes,
      },
      {
        onSuccess: (result) => {
          router.push(`/analysis/${result.id}`);
        },
      }
    );
  };

  const toggleBetaType = (type: string) => {
    setSelectedBetaTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  if (isAnalyzing) {
    return (
      <PageLayout maxWidth="md">
        <div className="min-h-[60vh] flex flex-col items-center justify-center gap-6">
          <LoadingSpinner size="xl" />
          <div className="text-center">
            <h2 className="text-xl font-bold text-white mb-2">Analyzing Route</h2>
            <p className="text-slate-400 animate-pulse">{analysisProgress}</p>
          </div>
          <div className="text-xs text-slate-600 max-w-xs text-center">
            CV pipeline, route identification, and beta generation typically takes 30–90 seconds.
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Import Route" maxWidth="2xl">
      <div className="space-y-6">
        {/* Upload */}
        <Card header={<span className="font-semibold text-slate-200">Upload Photos</span>}>
          <ImageUpload files={files} onFilesChange={setFiles} maxFiles={10} />
          <p className="text-xs text-slate-600 mt-2">
            Upload 1–10 photos of the wall. Multiple angles improve accuracy.
            Include the entire wall in at least one image.
          </p>
        </Card>

        {/* Options */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Board type */}
          <Card header={<span className="font-semibold text-slate-200">Board Type</span>}>
            <select
              value={boardType}
              onChange={(e) => setBoardType(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              {BOARD_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </Card>

          {/* Climber profile */}
          <Card header={<span className="font-semibold text-slate-200">Climber Profile</span>}>
            <select
              value={selectedProfileId}
              onChange={(e) => setSelectedProfileId(e.target.value)}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              <option value="">Default Profile (average climber)</option>
              {profiles?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <p className="text-xs text-slate-600 mt-1.5">
              Create a profile for personalized beta →{' '}
              <a href="/profile" className="text-accent-400 hover:underline">Profile page</a>
            </p>
          </Card>
        </div>

        {/* Beta types */}
        <Card header={<span className="font-semibold text-slate-200">Beta Types to Generate</span>}>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {BETA_TYPE_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => toggleBetaType(value)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors text-left ${
                  selectedBetaTypes.includes(value)
                    ? 'bg-accent-500/20 text-accent-400 border border-accent-500/30'
                    : 'bg-slate-800 text-slate-500 border border-slate-700 hover:border-slate-600'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-600 mt-2">
            Each beta type generates a distinct movement sequence. More types = longer processing.
          </p>
        </Card>

        {/* Notes */}
        <Card header={<span className="font-semibold text-slate-200">Notes (optional)</span>}>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="e.g. 'V6 yellow route, right side of wall, start holds are the two lowest yellows'"
            rows={2}
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accent-500 resize-none"
          />
        </Card>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            <AlertTriangle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400">Analysis failed</p>
              <p className="text-xs text-red-400/80 mt-0.5">{error.message}</p>
            </div>
          </div>
        )}

        <Button
          onClick={handleAnalyze}
          disabled={files.length === 0 || selectedBetaTypes.length === 0}
          loading={isPending}
          size="lg"
          className="w-full"
          leftIcon={<Upload size={18} />}
        >
          {files.length === 0
            ? 'Select images to analyze'
            : `Analyze ${files.length} image${files.length !== 1 ? 's' : ''}`}
        </Button>
      </div>
    </PageLayout>
  );
};

export default ImportPage;
