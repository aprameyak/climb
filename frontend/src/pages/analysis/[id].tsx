import type { NextPage } from 'next';
import { useRouter } from 'next/router';
import { useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { WallCanvas } from '@/components/wall/WallCanvas';
import { HoldDetails } from '@/components/wall/HoldDetails';
import { BetaPanel } from '@/components/beta/BetaPanel';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { useAnalysis } from '@/hooks/useAnalysis';
import { useAppStore } from '@/store/useAppStore';
import { getImageUrl } from '@/api/client';
import { wallAngleToDescription } from '@/utils/colors';
import type { DetectedHold } from '@/types';
import { AlertTriangle, ArrowLeft, Eye, Info } from 'lucide-react';
import Link from 'next/link';

const AnalysisPage: NextPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { data: analysis, isLoading, error } = useAnalysis(typeof id === 'string' ? id : null);
  const { activeMove, activeBetaType, selectedHoldId, setSelectedHoldId } = useAppStore();

  const [showAllHolds, setShowAllHolds] = useState(true);

  if (isLoading) return <PageLayout><LoadingSpinner size="xl" label="Loading analysis..." /></PageLayout>;
  if (error || !analysis) {
    return (
      <PageLayout>
        <EmptyState
          icon={<Eye size={48} />}
          title="Analysis not found"
          description="This analysis may have been deleted or doesn't exist"
          action={<Link href="/history"><Button>View History</Button></Link>}
        />
      </PageLayout>
    );
  }

  const { vision_result, betas, difficulty } = analysis;
  const activeBeta = betas.find((b) => b.beta_type === activeBetaType);
  const activeMove_ = activeBeta?.moves.find((m) => m.move_number === activeMove) ?? null;
  const selectedHold: DetectedHold | undefined = vision_result.holds.find(
    (h) => h.id === selectedHoldId
  );

  const imageUrl = getImageUrl(vision_result.image_path);
  const holds = showAllHolds ? vision_result.holds : (vision_result.active_route?.holds ?? vision_result.holds);

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Top bar */}
      <div className="sticky top-0 z-30 bg-slate-900/95 backdrop-blur border-b border-slate-700/50 px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/history">
              <button className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                <ArrowLeft size={18} />
              </button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                {difficulty && (
                  <>
                    <Badge variant="accent">V{difficulty.grade_v_estimate}</Badge>
                    <Badge variant="muted">{difficulty.grade_font_estimate}</Badge>
                  </>
                )}
                <Badge
                  variant={
                    vision_result.overall_confidence >= 0.7
                      ? 'success'
                      : vision_result.overall_confidence >= 0.5
                      ? 'warning'
                      : 'danger'
                  }
                >
                  {(vision_result.overall_confidence * 100).toFixed(0)}% confidence
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {vision_result.holds.length} holds · {betas.length} beta sequences ·{' '}
                {vision_result.processing_time_ms.toFixed(0)}ms
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAllHolds(!showAllHolds)}
              className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${
                showAllHolds ? 'bg-accent-500/20 text-accent-400' : 'bg-slate-800 text-slate-400'
              }`}
            >
              {showAllHolds ? 'All Holds' : 'Route Holds'}
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        {/* Warnings */}
        {vision_result.warnings.length > 0 && (
          <div className="mb-4 space-y-1">
            {vision_result.warnings.slice(0, 3).map((w, i) => (
              <div
                key={i}
                className="flex items-start gap-2 text-xs text-yellow-500 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2"
              >
                <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                {w}
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
          {/* Wall canvas */}
          <div className="relative">
            <div className="rounded-xl overflow-hidden bg-slate-900 border border-slate-700/50" style={{ height: '65vh', minHeight: 400 }}>
              <WallCanvas
                imageUrl={imageUrl}
                holds={holds}
                currentMove={activeMove_}
                selectedHoldId={selectedHoldId}
                onHoldSelect={setSelectedHoldId}
              />
            </div>

            {/* Hold details popover */}
            {selectedHold && (
              <div className="absolute top-4 left-4 z-10">
                <HoldDetails hold={selectedHold} onClose={() => setSelectedHoldId(null)} />
              </div>
            )}

            {/* Wall info overlay */}
            {vision_result.wall_geometry && (
              <div className="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur rounded-lg px-3 py-2 text-xs text-slate-400">
                {wallAngleToDescription(vision_result.wall_geometry.angle_degrees)} ·{' '}
                {vision_result.wall_geometry.angle_degrees.toFixed(0)}° ·{' '}
                {vision_result.wall_geometry.height_m.toFixed(1)}m ×{' '}
                {vision_result.wall_geometry.width_m.toFixed(1)}m
              </div>
            )}
          </div>

          {/* Beta panel */}
          <div className="h-[65vh] min-h-[400px] flex flex-col">
            <BetaPanel analysis={analysis} />
          </div>
        </div>

        {/* Difficulty breakdown */}
        {difficulty && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card header={<span className="text-sm font-semibold text-slate-200">Difficulty</span>}>
              <div className="space-y-2">
                <ConfidenceBar value={difficulty.power_intensity} label="Power" size="sm" />
                <ConfidenceBar value={difficulty.finger_intensity} label="Finger" size="sm" />
                <ConfidenceBar value={difficulty.core_intensity} label="Core" size="sm" />
                <ConfidenceBar value={difficulty.coordination_intensity} label="Coordination" size="sm" />
                <ConfidenceBar value={difficulty.balance_intensity} label="Balance" size="sm" />
                <ConfidenceBar value={difficulty.mobility_intensity} label="Mobility" size="sm" />
              </div>
            </Card>
            <Card header={<span className="text-sm font-semibold text-slate-200">Crux</span>}>
              <p className="text-sm text-slate-300">{difficulty.crux_description}</p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <div>
                  <div className="text-xs text-slate-500">Flash Prob</div>
                  <div className="text-lg font-bold text-yellow-400">
                    {(difficulty.flash_probability * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Send Prob</div>
                  <div className="text-lg font-bold text-green-400">
                    {(difficulty.send_probability * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </Card>
            <Card header={<span className="text-sm font-semibold text-slate-200">Detection</span>}>
              <div className="space-y-2">
                {Object.entries(vision_result.confidence_breakdown).map(([key, val]) => (
                  <ConfidenceBar
                    key={key}
                    value={val}
                    label={key.replace(/_/g, ' ')}
                    size="sm"
                  />
                ))}
              </div>
              {vision_result.requires_additional_images && (
                <div className="mt-3 flex items-start gap-1.5 text-xs text-yellow-500">
                  <Info size={12} className="mt-0.5" />
                  Additional images would improve accuracy
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisPage;
