import { useState } from 'react';
import { clsx } from 'clsx';
import type { BetaSolution, ClimbingMove, DetectedHold } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { LIMB_COLORS, difficultyToColor, moveTypeToLabel } from '@/utils/colors';
import { AlertTriangle, ChevronDown, ChevronUp, Zap } from 'lucide-react';

interface MoveCardProps {
  move: ClimbingMove;
  isActive: boolean;
  holdsMap: Map<string, DetectedHold>;
  onClick?: () => void;
  beta?: BetaSolution;
}

function LimbIndicator({
  holdId,
  label,
  color,
  holdsMap,
}: {
  holdId: string | null;
  label: string;
  color: string;
  holdsMap: Map<string, DetectedHold>;
}) {
  const hold = holdId ? holdsMap.get(holdId) : null;
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <div
        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <div className="min-w-0">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="text-xs text-slate-300 truncate font-mono">
          {hold ? hold.hold_type.replace(/_/g, ' ') : holdId ? holdId.slice(0, 8) : '—'}
        </div>
      </div>
    </div>
  );
}

export function MoveCard({ move, isActive, holdsMap, onClick, beta }: MoveCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isCrux = move.is_crux;

  return (
    <Card
      variant={isCrux ? 'crux' : isActive ? 'highlighted' : 'default'}
      className={clsx(
        'transition-all duration-200',
        isActive && 'ring-1 ring-accent-500/50',
        onClick && 'cursor-pointer hover:bg-slate-800'
      )}
      onClick={onClick}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <div
            className={clsx(
              'w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold',
              isActive
                ? 'bg-accent-500 text-white'
                : isCrux
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'bg-slate-700 text-slate-300'
            )}
          >
            {move.move_number}
          </div>
          <div className="flex flex-wrap gap-1">
            {move.move_types.slice(0, 3).map((mt) => (
              <Badge key={mt} variant={isCrux ? 'danger' : isActive ? 'accent' : 'default'} size="sm">
                {moveTypeToLabel(mt)}
              </Badge>
            ))}
            {isCrux && (
              <Badge variant="danger" size="sm">
                <Zap size={10} />
                CRUX
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <div
            className="text-xs font-bold"
            style={{ color: difficultyToColor(move.difficulty_rating) }}
          >
            {(move.difficulty_rating * 10).toFixed(1)}
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-300 mb-3 leading-relaxed">{move.description}</p>

      {/* Limb grid */}
      <div className="grid grid-cols-2 gap-2 mb-3 p-2 bg-slate-900/50 rounded-lg">
        <LimbIndicator
          holdId={move.body_position.left_hand.hold_id}
          label="Left Hand"
          color={LIMB_COLORS.lh}
          holdsMap={holdsMap}
        />
        <LimbIndicator
          holdId={move.body_position.right_hand.hold_id}
          label="Right Hand"
          color={LIMB_COLORS.rh}
          holdsMap={holdsMap}
        />
        <LimbIndicator
          holdId={move.body_position.left_foot.hold_id}
          label="Left Foot"
          color={LIMB_COLORS.lf}
          holdsMap={holdsMap}
        />
        <LimbIndicator
          holdId={move.body_position.right_foot.hold_id}
          label="Right Foot"
          color={LIMB_COLORS.rf}
          holdsMap={holdsMap}
        />
      </div>

      {/* Bars */}
      <div className="space-y-1.5 mb-3">
        <ConfidenceBar value={move.confidence} label="Confidence" size="sm" />
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Energy</span>
          <div className="flex-1 mx-2 h-1 rounded-full bg-slate-700">
            <div
              className="h-full rounded-full bg-yellow-500"
              style={{ width: `${move.energy_cost * 100}%` }}
            />
          </div>
          <span className="text-slate-400 font-mono">{(move.energy_cost * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Toggle expand */}
      <button
        className="w-full flex items-center justify-between text-xs text-slate-500 hover:text-slate-300 transition-colors py-1"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        <span>Details</span>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-slate-700/50 pt-3">
          {/* Reasoning */}
          <div>
            <p className="text-xs font-semibold text-slate-400 mb-1">Why this move</p>
            <p className="text-xs text-slate-400 leading-relaxed">{move.reasoning}</p>
          </div>

          {/* Common mistakes */}
          {move.common_mistakes.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1">
                <AlertTriangle size={11} className="text-yellow-500" />
                Common mistakes
              </p>
              <ul className="space-y-1">
                {move.common_mistakes.map((m, i) => (
                  <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                    <span className="text-yellow-600 mt-0.5">•</span>
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Alternatives */}
          {move.alternative_options.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-1">Alternatives</p>
              <ul className="space-y-1">
                {move.alternative_options.map((a, i) => (
                  <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                    <span className="text-blue-500 mt-0.5">→</span>
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Physics note */}
          {move.physics_note && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-2">
              <p className="text-xs text-blue-400">{move.physics_note}</p>
            </div>
          )}

          {/* Body position details */}
          <div>
            <p className="text-xs font-semibold text-slate-400 mb-1">Body Position</p>
            <div className="text-xs text-slate-500 space-y-0.5">
              <div>Torso: {move.body_position.torso_rotation_deg > 0 ? 'Right side in' : move.body_position.torso_rotation_deg < 0 ? 'Left side in' : 'Square'}</div>
              <div>Head: {move.body_position.head_direction}</div>
              <div>
                Weight: LH {(move.body_position.weight_distribution['lh'] * 100 || 0).toFixed(0)}%{' '}
                RH {(move.body_position.weight_distribution['rh'] * 100 || 0).toFixed(0)}%{' '}
                LF {(move.body_position.weight_distribution['lf'] * 100 || 0).toFixed(0)}%{' '}
                RF {(move.body_position.weight_distribution['rf'] * 100 || 0).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
