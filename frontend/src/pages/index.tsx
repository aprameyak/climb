import type { NextPage } from 'next';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Brain,
  Camera,
  ChartBar,
  Eye,
  Move,
  Upload,
  User,
  Zap,
} from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/Button';
import { useAnalysisList } from '@/hooks/useAnalysis';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

const FEATURES = [
  {
    icon: Eye,
    title: 'Computer Vision Pipeline',
    description:
      'Claude Vision AI detects holds, classifies types, estimates orientation and friction, identifies route markers.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: User,
    title: 'Biomechanics Engine',
    description:
      'Full anthropometric model. Reach volume, joint constraints, balance analysis — every move validated against your body.',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
  },
  {
    icon: Brain,
    title: 'AI Beta Solver',
    description:
      'Claude generates personalized move sequences — static, dynamic, energy-efficient, and more — with full reasoning.',
    color: 'text-accent-400',
    bg: 'bg-accent-500/10',
  },
  {
    icon: ChartBar,
    title: 'Physics Simulation',
    description:
      'Friction, momentum, balance, barn-door risk, deadpoint physics — grounded in real biomechanics literature.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
];

const Home: NextPage = () => {
  const { data: analyses } = useAnalysisList();

  return (
    <PageLayout maxWidth="7xl">
      {/* Hero */}
      <section className="py-12 sm:py-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-accent-500/10 border border-accent-500/20 rounded-full text-xs text-accent-400 font-medium mb-6">
            <Zap size={12} />
            Powered by Claude Vision + Biomechanics Engine
          </div>
          <h1 className="text-4xl sm:text-6xl font-black text-white mb-4 tracking-tight">
            AI-Powered{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent-400 to-orange-300">
              Bouldering Beta
            </span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-8 leading-relaxed">
            Upload photos of any boulder problem. Get personalized, biomechanically validated
            move sequences — adapted to your height, strength, and flexibility.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link href="/import">
              <Button size="lg" leftIcon={<Upload size={18} />}>
                Upload Photos
              </Button>
            </Link>
            <Link href="/camera">
              <Button size="lg" variant="secondary" leftIcon={<Camera size={18} />}>
                Use Camera
              </Button>
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="mb-12">
        <h2 className="text-xl font-bold text-white mb-6 text-center">
          Built for Serious Climbers
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="h-full">
                  <div
                    className={`w-10 h-10 rounded-xl ${feature.bg} flex items-center justify-center mb-3`}
                  >
                    <Icon size={20} className={feature.color} />
                  </div>
                  <h3 className="font-semibold text-slate-200 mb-2 text-sm">{feature.title}</h3>
                  <p className="text-xs text-slate-500 leading-relaxed">{feature.description}</p>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* Recent analyses */}
      {analyses && analyses.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Recent Analyses</h2>
            <Link href="/history">
              <Button variant="ghost" size="sm">View all</Button>
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {analyses.slice(0, 6).map((analysis) => (
              <Link key={analysis.id} href={`/analysis/${analysis.id}`}>
                <Card
                  className="hover:border-slate-600 transition-colors cursor-pointer"
                  onClick={() => {}}
                >
                  <div className="flex items-start justify-between mb-2">
                    {analysis.grade_font ? (
                      <Badge variant="accent">{analysis.grade_font}</Badge>
                    ) : (
                      <Badge variant="muted">Unknown grade</Badge>
                    )}
                    <Badge
                      variant={
                        analysis.overall_confidence >= 0.7
                          ? 'success'
                          : analysis.overall_confidence >= 0.5
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      {(analysis.overall_confidence * 100).toFixed(0)}% confidence
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">
                    {analysis.hold_count} holds · {analysis.beta_count} beta sequences
                  </p>
                  <p className="text-xs text-slate-600 mt-1">
                    {new Date(analysis.created_at).toLocaleDateString()}
                  </p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Empty state CTA */}
      {(!analyses || analyses.length === 0) && (
        <section className="text-center py-8">
          <div className="max-w-sm mx-auto">
            <Move size={48} className="mx-auto text-slate-700 mb-4" />
            <h3 className="text-lg font-semibold text-slate-400 mb-2">No analyses yet</h3>
            <p className="text-sm text-slate-600 mb-4">
              Upload photos of a boulder problem to get started
            </p>
            <Link href="/import">
              <Button leftIcon={<Upload size={16} />}>Upload Your First Problem</Button>
            </Link>
          </div>
        </section>
      )}
    </PageLayout>
  );
};

export default Home;
