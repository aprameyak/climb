import type { NextPage } from 'next';
import { useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useDeleteAnalysis } from '@/hooks/useAnalysis';
import { useAnalysisList } from '@/hooks/useAnalysis';
import { useAppStore } from '@/store/useAppStore';
import { AlertTriangle, CheckCircle, Info, Trash2 } from 'lucide-react';

const SettingsPage: NextPage = () => {
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  );
  const [healthStatus, setHealthStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const { data: analyses } = useAnalysisList();
  const { mutate: deleteAnalysis } = useDeleteAnalysis();
  const { setCurrentAnalysis, setCurrentProfile } = useAppStore();

  const checkHealth = async () => {
    try {
      const res = await fetch(`${apiUrl}/health`);
      setHealthStatus(res.ok ? 'ok' : 'error');
    } catch {
      setHealthStatus('error');
    }
  };

  const clearHistory = () => {
    if (!analyses) return;
    if (!confirm(`Delete all ${analyses.length} analyses?`)) return;
    analyses.forEach((a) => deleteAnalysis(a.id));
    setCurrentAnalysis(null);
  };

  return (
    <PageLayout title="Settings" maxWidth="2xl">
      <div className="space-y-6">
        {/* API config */}
        <Card header={<span className="font-semibold text-slate-200">Backend API</span>}>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1">API URL</label>
              <div className="flex gap-2">
                <input
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500 font-mono"
                />
                <Button variant="secondary" size="sm" onClick={checkHealth}>
                  Test
                </Button>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Set NEXT_PUBLIC_API_URL env var to persist this setting
              </p>
            </div>
            {healthStatus === 'ok' && (
              <div className="flex items-center gap-2 text-sm text-green-400">
                <CheckCircle size={14} /> API is reachable
              </div>
            )}
            {healthStatus === 'error' && (
              <div className="flex items-center gap-2 text-sm text-red-400">
                <AlertTriangle size={14} /> Cannot reach API — is the backend running?
              </div>
            )}
          </div>
        </Card>

        {/* Data management */}
        <Card header={<span className="font-semibold text-slate-200">Data</span>}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-300">Analysis History</p>
                <p className="text-xs text-slate-500">{analyses?.length ?? 0} analyses stored</p>
              </div>
              <Button
                variant="danger"
                size="sm"
                disabled={!analyses || analyses.length === 0}
                onClick={clearHistory}
                leftIcon={<Trash2 size={14} />}
              >
                Clear All
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-300">Current Profile</p>
                <p className="text-xs text-slate-500">Reset active climber profile</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentProfile(null)}
              >
                Reset
              </Button>
            </div>
          </div>
        </Card>

        {/* About */}
        <Card header={<span className="font-semibold text-slate-200">About</span>}>
          <div className="space-y-2 text-xs text-slate-500">
            <p><span className="text-slate-400 font-medium">Climb.AI</span> — AI-powered bouldering beta solver</p>
            <p>Version 1.0.0</p>
            <div className="flex items-start gap-2 mt-3 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <Info size={14} className="text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-blue-400/80">
                Computer vision and beta generation use Claude Vision AI (claude-sonnet-4-6).
                An Anthropic API key is required in the backend .env file.
                Hold detection confidence reflects the AI&apos;s uncertainty — low confidence
                results require additional photos.
              </div>
            </div>
          </div>
        </Card>
      </div>
    </PageLayout>
  );
};

export default SettingsPage;
