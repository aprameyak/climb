import { clsx } from 'clsx';
import type { AnalysisResult, BetaSolution, BetaType } from '@/types';
import { MoveCard } from './MoveCard';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { betaTypeToLabel } from '@/utils/colors';
import { useAppStore } from '@/store/useAppStore';
import { ChevronLeft, ChevronRight, Dumbbell } from 'lucide-react';

interface BetaPanelProps {
  analysis: AnalysisResult;
}

export function BetaPanel({ analysis }: BetaPanelProps) {
  const { activeBetaType, setActiveBetaType, activeMove, setActiveMove, nextMove, prevMove } =
    useAppStore();

  const holdsMap = new Map(
    analysis.vision_result.holds.map((h) => [h.id, h])
  );

  const beta = analysis.betas.find((b) => b.beta_type === activeBetaType);
  const availableBetaTypes = analysis.betas.map((b) => b.beta_type);

  const currentMove = beta?.moves.find((m) => m.move_number === activeMove) ?? null;
  const totalMoves = beta?.moves.length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Beta type tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 mb-3 scrollbar-none">
        {availableBetaTypes.map((type) => (
          <button
            key={type}
            onClick={() => setActiveBetaType(type as BetaType)}
            className={clsx(
              'flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap',
              activeBetaType === type
                ? 'bg-accent-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            )}
          >
            {betaTypeToLabel(type as BetaType)}
          </button>
        ))}
      </div>

      {/* Beta stats */}
      {beta && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3 mb-3">
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <div className="text-xs text-slate-500 mb-1">Moves</div>
              <div className="text-lg font-bold text-white">{beta.moves.length}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Send Probability</div>
              <div className="text-lg font-bold text-green-400">
                {(beta.expected_send_probability * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Flash Probability</div>
              <div className="text-lg font-bold text-yellow-400">
                {(beta.expected_flash_probability * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-1">Energy Cost</div>
              <div className="text-lg font-bold text-slate-300">
                {(beta.total_energy_cost * 100).toFixed(0)}%
              </div>
            </div>
          </div>
          <ConfidenceBar value={beta.overall_confidence} label="Beta Confidence" />
          {beta.crux_move_numbers.length > 0 && (
            <div className="mt-2 flex items-center gap-2 text-xs">
              <span className="text-slate-500">Crux:</span>
              {beta.crux_move_numbers.map((n) => (
                <Badge key={n} variant="danger" size="sm">Move {n}</Badge>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Move navigation */}
      {beta && totalMoves > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={prevMove}
            disabled={activeMove === 1 || activeMove === null}
            leftIcon={<ChevronLeft size={14} />}
          >
            Prev
          </Button>
          <div className="flex-1 text-center text-sm text-slate-400">
            Move{' '}
            <span className="font-bold text-white">
              {activeMove ?? 1}
            </span>{' '}
            / {totalMoves}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={nextMove}
            disabled={activeMove === totalMoves}
            rightIcon={<ChevronRight size={14} />}
          >
            Next
          </Button>
        </div>
      )}

      {/* Move list */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-slate-700">
        {!beta ? (
          <EmptyState
            icon={<Dumbbell size={36} />}
            title="No beta available"
            description="Select a beta type to view movement sequences"
          />
        ) : beta.moves.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500">Beta generation encountered an issue</p>
            {beta.generation_warnings.map((w, i) => (
              <p key={i} className="text-xs text-red-400 mt-1">{w}</p>
            ))}
          </div>
        ) : (
          beta.moves.map((move) => (
            <MoveCard
              key={move.move_number}
              move={move}
              isActive={move.move_number === activeMove}
              holdsMap={holdsMap}
              beta={beta}
              onClick={() => setActiveMove(move.move_number)}
            />
          ))
        )}
      </div>

      {/* Warnings */}
      {beta?.generation_warnings && beta.generation_warnings.length > 0 && (
        <div className="mt-2 space-y-1">
          {beta.generation_warnings.map((w, i) => (
            <div
              key={i}
              className="text-xs text-yellow-500 bg-yellow-500/10 border border-yellow-500/20 rounded px-2 py-1"
            >
              {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
