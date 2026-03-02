import React, { useRef, useState, useCallback, useEffect } from 'react';

/** 区域选择输出：矩形或遮罩 */
export type RegionData =
  | { type: 'rect'; coordinates: [[number, number], [number, number]] }
  | { type: 'mask'; mask_data: string };

interface RegionCanvasProps {
  /** 参考图 base64（不含 data URL 前缀）或 data URL */
  imageBase64: string | null;
  /** 区域选择变化回调 */
  onChange: (data: RegionData | null) => void;
  /** 当前选中的区域（受控） */
  value?: RegionData | null;
  /** 占位提示 */
  placeholder?: string;
  /** 容器高度 */
  height?: number;
}

/**
 * RegionCanvas - 在参考图上支持矩形框选区域
 *
 * Props:
 * - imageBase64: 图片 base64，未上传时显示 placeholder
 * - onChange: 圈选完成时回调，输出 { type: 'rect', coordinates: [[x1,y1],[x2,y2]] }，坐标为相对比例 [0-1]
 * - value: 受控模式下的当前值（可选）
 * - placeholder: 无图时的提示文案
 * - height: 容器高度，默认 160
 *
 * 输出格式（与后端 RegionSelect 一致）:
 * - rect: { type: 'rect', coordinates: [[x1,y1],[x2,y2]] }，左上角到右下角，归一化坐标
 * - mask: { type: 'mask', mask_data: base64 }（当前仅实现 rect）
 */
const RegionCanvas: React.FC<RegionCanvasProps> = ({
  imageBase64,
  onChange,
  value = null,
  placeholder = '请先上传图片',
  height = 160,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);
  const [current, setCurrent] = useState<{ x: number; y: number } | null>(null);
  const [contentRect, setContentRect] = useState<{ left: number; top: number; width: number; height: number } | null>(null);

  /** 获取图片实际显示区域（object-contain 时可能有留白），返回 client 坐标 */
  const getImageContentRect = useCallback(() => {
    const img = imgRef.current;
    if (!img || img.naturalWidth === 0 || img.naturalHeight === 0) return null;
    const rect = img.getBoundingClientRect();
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    const scale = Math.min(rect.width / nw, rect.height / nh);
    const dw = nw * scale;
    const dh = nh * scale;
    const left = rect.left + (rect.width - dw) / 2;
    const top = rect.top + (rect.height - dh) / 2;
    return { left, top, width: dw, height: dh };
  }, []);

  useEffect(() => {
    if (!imageBase64) return;
    const update = () => {
      const r = getImageContentRect();
      const container = containerRef.current;
      if (r && container) {
        const cr = container.getBoundingClientRect();
        setContentRect({
          left: r.left - cr.left,
          top: r.top - cr.top,
          width: r.width,
          height: r.height,
        });
      }
    };
    const img = imgRef.current;
    if (img) {
      img.addEventListener('load', update);
      if (img.complete) update();
    }
    const ro = new ResizeObserver(update);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => {
      img?.removeEventListener('load', update);
      ro.disconnect();
    };
  }, [imageBase64, getImageContentRect]);

  const toNormalized = useCallback(
    (clientX: number, clientY: number): [number, number] | null => {
      const rect = getImageContentRect();
      if (!rect || rect.width <= 0 || rect.height <= 0) return null;
      const x = (clientX - rect.left) / rect.width;
      const y = (clientY - rect.top) / rect.height;
      const xNorm = Math.max(0, Math.min(1, x));
      const yNorm = Math.max(0, Math.min(1, y));
      return [xNorm, yNorm];
    },
    [getImageContentRect]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!imageBase64) return;
      const norm = toNormalized(e.clientX, e.clientY);
      if (!norm) return;
      setStart({ x: norm[0], y: norm[1] });
      setCurrent({ x: norm[0], y: norm[1] });
      setIsDrawing(true);
    },
    [imageBase64, toNormalized]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!isDrawing || !start) return;
      const norm = toNormalized(e.clientX, e.clientY);
      if (!norm) return;
      setCurrent({ x: norm[0], y: norm[1] });
    },
    [isDrawing, start, toNormalized]
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawing || !start || !current) {
      setIsDrawing(false);
      setStart(null);
      setCurrent(null);
      return;
    }
    const x1 = Math.min(start.x, current.x);
    const y1 = Math.min(start.y, current.y);
    const x2 = Math.max(start.x, current.x);
    const y2 = Math.max(start.y, current.y);
    const w = x2 - x1;
    const h = y2 - y1;
    if (w < 0.02 || h < 0.02) {
      onChange(null);
    } else {
      onChange({
        type: 'rect',
        coordinates: [
          [x1, y1],
          [x2, y2],
        ],
      });
    }
    setIsDrawing(false);
    setStart(null);
    setCurrent(null);
  }, [isDrawing, start, current, onChange]);

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onChange(null);
    },
    [onChange]
  );

  const displayCoords = value?.type === 'rect' ? value.coordinates : null;
  const drawStart = isDrawing ? start : displayCoords?.[0] ? { x: displayCoords[0][0], y: displayCoords[0][1] } : null;
  const drawEnd = isDrawing ? current : displayCoords?.[1] ? { x: displayCoords[1][0], y: displayCoords[1][1] } : null;

  const imgSrc = imageBase64
    ? imageBase64.startsWith('data:')
      ? imageBase64
      : `data:image/png;base64,${imageBase64}`
    : null;

  if (!imgSrc) {
    return (
      <div
        className="w-full border border-dashed border-white/20 flex items-center justify-center text-white/30 text-xs bg-white/5"
        style={{ height }}
      >
        {placeholder}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full overflow-hidden border border-white/10 bg-black/20"
      style={{ height }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <img
        ref={imgRef}
        src={imgSrc}
        alt="Region reference"
        className="w-full h-full object-contain select-none pointer-events-none"
        draggable={false}
      />
      {drawStart && drawEnd && contentRect && (
        <svg
          className="absolute pointer-events-none"
          style={{
            left: contentRect.left,
            top: contentRect.top,
            width: contentRect.width,
            height: contentRect.height,
          }}
          viewBox="0 0 1 1"
          preserveAspectRatio="none"
        >
          <rect
            x={Math.min(drawStart.x, drawEnd.x)}
            y={Math.min(drawStart.y, drawEnd.y)}
            width={Math.abs(drawEnd.x - drawStart.x)}
            height={Math.abs(drawEnd.y - drawStart.y)}
            fill="rgba(226,232,92,0.2)"
            stroke="#E2E85C"
            strokeWidth={0.008}
          />
        </svg>
      )}
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute top-1 right-1 px-2 py-0.5 text-[10px] bg-black/60 hover:bg-[#E2E85C] text-white hover:text-black transition-colors"
        >
          清除
        </button>
      )}
      <div className="absolute bottom-1 left-1 text-[10px] text-white/40">
        拖拽绘制矩形框选区域
      </div>
    </div>
  );
};

export default RegionCanvas;
