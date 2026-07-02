import type { NextPage } from 'next';
import Link from 'next/link';
import { PageLayout } from '@/components/layout/PageLayout';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useAnalysisList, useDeleteAnalysis } from '@/hooks/useAnalysis';
import { getImageUrl } from '@/api/client';
import { History, Trash2, Upload } from 'lucide-react';

const HistoryPage: NextPage = () => {
  const { data: analyses, isLoading } = useAnalysisList();
  const { mutate: deleteAnalysis, isPending: isDeleting } = useDeleteAnalysis();

  if (isLoading) return <PageLayout><LoadingSpinner size="lg" /></PageLayout>;

  return (
    <PageLayout title="Analysis History" maxWidth="7xl">
      {!analyses || analyses.length === 0 ? (
        <EmptyState
          icon={<History size={48} />}
          title="No analyses yet"
          description="Analyze a boulder problem to see it appear here"
          action={
            <Link href="/import">
              <Button leftIcon={<Upload size={16} />}>Upload Route</Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {analyses.map((analysis) => {
            const imageUrl = analysis.image_path ? getImageUrl(analysis.image_path) : null;
            return (
              <Card key={analysis.id} className="overflow-hidden p-0">
                {/* Thumbnail */}
                <Link href={`/analysis/${analysis.id}`}>
                  <div className="h-36 bg-slate-800 relative overflow-hidden">
                    {imageUrl ? (
                      <img
                        src={imageUrl}
                        alt="Wall"
                        className="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600">
                        <History size={32} />
                      </div>
                    )}
                    {analysis.grade_font && (
                      <div className="absolute top-2 left-2">
                        <Badge variant="accent">{analysis.grade_font}</Badge>
                      </div>
                    )}
                    <div className="absolute top-2 right-2">
                      <Badge
                        variant={
                          analysis.overall_confidence >= 0.7
                            ? 'success'
                            : analysis.overall_confidence >= 0.5
                            ? 'warning'
                            : 'danger'
                        }
                      >
                        {(analysis.overall_confidence * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                </Link>

                {/* Info */}
                <div className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs text-slate-400">
                      {new Date(analysis.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                    <button
                      onClick={() => deleteAnalysis(analysis.id)}
                      disabled={isDeleting}
                      className="text-slate-600 hover:text-red-400 transition-colors p-0.5"
                      title="Delete analysis"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <p className="text-xs text-slate-500">
                    {analysis.hold_count} holds · {analysis.beta_count} betas
                  </p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
};

export default HistoryPage;
