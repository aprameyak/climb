import type { DetectedHold } from '@/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { holdTypeToColor } from '@/utils/colors';
import { X } from 'lucide-react';

interface HoldDetailsProps {
  hold: DetectedHold;
  onClose: () => void;
}

export function HoldDetails({ hold, onClose }: HoldDetailsProps) {
  const holdColor = holdTypeToColor(hold.hold_type);

  return (
    <Card className="w-72">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-4 h-4 rounded-full border-2 border-white/20"
            style={{ backgroundColor: holdColor }}
          />
          <span className="font-semibold text-white capitalize">
            {hold.hold_type.replace(/_/g, ' ')}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X size={16} />
        </button>
      </div>

      <div className="space-y-3">
        <ConfidenceBar value={hold.confidence} label="Detection Confidence" />

        {/* Markers */}
        {(hold.is_start || hold.is_finish) && (
          <div className="flex gap-2">
            {hold.is_start && <Badge variant="success">START</Badge>}
            {hold.is_finish && <Badge variant="danger">FINISH</Badge>}
          </div>
        )}

        {/* Grip direction */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Grip Direction</span>
          <span className="text-slate-200 capitalize">
            {hold.grip_direction.replace(/_/g, ' ')}
          </span>
        </div>

        {/* Difficulty */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Difficulty</span>
          <span className="text-slate-200">V{hold.estimated_difficulty.toFixed(1)}</span>
        </div>

        {/* Friction */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Friction</span>
          <span className="text-slate-200">{(hold.estimated_friction * 100).toFixed(0)}%</span>
        </div>

        {/* Orientation */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">Orientation</span>
          <span className="text-slate-200">{hold.orientation_degrees.toFixed(0)}°</span>
        </div>

        {/* Usability */}
        <div>
          <p className="text-xs text-slate-400 mb-1.5">Usability</p>
          <div className="grid grid-cols-2 gap-1">
            {[
              { label: 'L Hand', can: hold.usability.left_hand, q: hold.usability.quality_lh, color: '#3b82f6' },
              { label: 'R Hand', can: hold.usability.right_hand, q: hold.usability.quality_rh, color: '#ef4444' },
              { label: 'L Foot', can: hold.usability.left_foot, q: hold.usability.quality_lf, color: '#22c55e' },
              { label: 'R Foot', can: hold.usability.right_foot, q: hold.usability.quality_rf, color: '#f97316' },
            ].map(({ label, can, q, color }) => (
              <div
                key={label}
                className={`flex items-center justify-between px-2 py-1 rounded text-xs ${
                  can ? 'bg-slate-700/50' : 'bg-slate-800/30 opacity-40'
                }`}
              >
                <span className="text-slate-400">{label}</span>
                {can && (
                  <div
                    className="w-8 h-1 rounded-full"
                    style={{ backgroundColor: color, opacity: q }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Route */}
        {hold.route_id && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Route</span>
            <Badge variant="muted">{hold.route_id}</Badge>
          </div>
        )}
      </div>
    </Card>
  );
}
