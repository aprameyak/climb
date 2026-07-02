'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ClimbingMove, DetectedHold } from '@/types';
import { LIMB_COLORS, holdTypeToColor } from '@/utils/colors';
import { getHoldAtPoint, polygonToKonvaPoints } from '@/utils/geometry';

interface WallCanvasProps {
  imageUrl: string;
  holds: DetectedHold[];
  currentMove: ClimbingMove | null;
  selectedHoldId: string | null;
  onHoldSelect: (holdId: string | null) => void;
  width?: number;
  height?: number;
}

interface RenderedHold {
  hold: DetectedHold;
  isActive: boolean;
  activeLimb: 'lh' | 'rh' | 'lf' | 'rf' | null;
}

export function WallCanvas({
  imageUrl,
  holds,
  currentMove,
  selectedHoldId,
  onHoldSelect,
  width = 800,
  height = 600,
}: WallCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ w: width, h: height });

  // Responsive sizing
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: cw, height: ch } = entry.contentRect;
        if (cw > 0 && ch > 0) {
          setDimensions({ w: cw, h: ch });
        }
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Load background image
  useEffect(() => {
    if (!imageUrl) return;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      setImageLoaded(true);
    };
    img.onerror = () => {
      setImageLoaded(false);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Compute active holds from current move
  const activeHolds = new Map<string, 'lh' | 'rh' | 'lf' | 'rf'>();
  if (currentMove) {
    const bp = currentMove.body_position;
    if (bp.left_hand.hold_id) activeHolds.set(bp.left_hand.hold_id, 'lh');
    if (bp.right_hand.hold_id) activeHolds.set(bp.right_hand.hold_id, 'rh');
    if (bp.left_foot.hold_id) activeHolds.set(bp.left_foot.hold_id, 'lf');
    if (bp.right_foot.hold_id) activeHolds.set(bp.right_foot.hold_id, 'rf');
  }

  // Main draw function
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const { w, h } = dimensions;
    canvas.width = w;
    canvas.height = h;

    // Background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Draw background image
    if (imageLoaded && imageRef.current) {
      const img = imageRef.current;
      const scale = Math.min(w / img.naturalWidth, h / img.naturalHeight);
      const dw = img.naturalWidth * scale;
      const dh = img.naturalHeight * scale;
      const dx = (w - dw) / 2;
      const dy = (h - dh) / 2;
      ctx.drawImage(img, dx, dy, dw, dh);
    }

    // Draw holds
    for (const hold of holds) {
      if (hold.polygon.length < 3) continue;

      const activeLimb = activeHolds.get(hold.id) ?? null;
      const isSelected = hold.id === selectedHoldId;
      const isActive = activeLimb !== null;
      const isStart = hold.is_start;
      const isFinish = hold.is_finish;

      // Build polygon path
      ctx.beginPath();
      const pts = hold.polygon;
      ctx.moveTo(pts[0][0] * w, pts[0][1] * h);
      for (let i = 1; i < pts.length; i++) {
        ctx.lineTo(pts[i][0] * w, pts[i][1] * h);
      }
      ctx.closePath();

      // Fill
      const holdColor = holdTypeToColor(hold.hold_type);
      const alpha = Math.max(0.25, hold.confidence);

      if (isActive && activeLimb) {
        ctx.fillStyle = LIMB_COLORS[activeLimb] + 'cc';
      } else if (isSelected) {
        ctx.fillStyle = '#ffffff30';
      } else {
        ctx.fillStyle = holdColor + Math.round(alpha * 0.4 * 255).toString(16).padStart(2, '0');
      }
      ctx.fill();

      // Stroke
      if (isActive && activeLimb) {
        ctx.strokeStyle = LIMB_COLORS[activeLimb];
        ctx.lineWidth = 3;
      } else if (isStart) {
        ctx.strokeStyle = '#22c55e';
        ctx.lineWidth = 2.5;
      } else if (isFinish) {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2.5;
      } else if (isSelected) {
        ctx.strokeStyle = '#f97316';
        ctx.lineWidth = 2;
      } else {
        ctx.strokeStyle = holdColor;
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = Math.max(0.4, hold.confidence);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Limb indicator dot
      if (isActive && activeLimb) {
        const cx = hold.center.x * w;
        const cy = hold.center.y * h;
        ctx.beginPath();
        ctx.arc(cx, cy, 6, 0, Math.PI * 2);
        ctx.fillStyle = LIMB_COLORS[activeLimb];
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Label
        ctx.font = 'bold 9px monospace';
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(activeLimb.toUpperCase(), cx, cy);
      }
    }

    // Draw center of mass
    if (currentMove?.body_position.center_of_mass) {
      const com = currentMove.body_position.center_of_mass;
      const cx = com.x * w;
      const cy = com.y * h;

      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, Math.PI * 2);
      ctx.fillStyle = LIMB_COLORS.com + '80';
      ctx.fill();
      ctx.strokeStyle = LIMB_COLORS.com;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Cross hair
      ctx.beginPath();
      ctx.moveTo(cx - 10, cy);
      ctx.lineTo(cx + 10, cy);
      ctx.moveTo(cx, cy - 10);
      ctx.lineTo(cx, cy + 10);
      ctx.strokeStyle = LIMB_COLORS.com;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }, [holds, currentMove, selectedHoldId, imageLoaded, dimensions]);

  useEffect(() => {
    draw();
  }, [draw]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const hold = getHoldAtPoint(holds, x, y, dimensions.w, dimensions.h);
      onHoldSelect(hold ? hold.id : null);
    },
    [holds, dimensions, onHoldSelect]
  );

  return (
    <div ref={containerRef} className="w-full h-full relative" style={{ minHeight: 400 }}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className="w-full h-full cursor-crosshair"
        style={{ display: 'block' }}
      />
      {!imageLoaded && imageUrl && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50">
          <div className="text-sm text-slate-400">Loading image...</div>
        </div>
      )}
    </div>
  );
}
