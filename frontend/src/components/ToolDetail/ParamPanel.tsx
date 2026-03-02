import React from 'react';
import type { ToolParam } from '../../config/toolConfigs';

interface ParamPanelProps {
  params: ToolParam[];
  values: Record<string, string | number | boolean>;
  onChange: (key: string, value: string | number | boolean) => void;
}

function toSliderValue(
  value: string | number | boolean | undefined,
  fallback: string | number | boolean
): number {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  if (typeof fallback === 'number') return fallback;
  if (typeof fallback === 'string') {
    const parsed = Number(fallback);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

const ParamPanel: React.FC<ParamPanelProps> = ({ params, values, onChange }) => {
  if (params.length === 0) return null;

  return (
    <>
      {params.map((param) => (
        <div key={param.key} className="flex flex-col gap-3">
          <span className="text-white/60 text-xs">{param.label}</span>

          {param.type === 'select' && param.options && (
            <div className={`grid gap-2 ${param.options.length <= 3 ? 'grid-cols-3' : param.options.length <= 5 ? 'grid-cols-5' : 'grid-cols-3'}`}>
              {param.options.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => onChange(param.key, opt.value)}
                  className={`h-8 text-xs transition-colors border ${
                    String(values[param.key]) === opt.value
                      ? 'bg-[#E2E85C] text-black border-[#E2E85C]'
                      : 'bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          {param.type === 'slider' && (
            (() => {
              const sliderValue = toSliderValue(values[param.key], param.defaultValue);
              return (
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={param.min ?? 0}
                    max={param.max ?? 1}
                    step={param.step ?? 0.1}
                    value={sliderValue}
                    onChange={(e) => onChange(param.key, parseFloat(e.target.value))}
                    className="flex-1 accent-[#E2E85C] h-1"
                  />
                  <span className="text-white/60 text-xs w-8 text-right">
                    {sliderValue.toFixed(1)}
                  </span>
                </div>
              );
            })()
          )}

          {param.type === 'text' && (
            <input
              type="text"
              value={String(values[param.key] || '')}
              onChange={(e) => onChange(param.key, e.target.value)}
              className="w-full h-8 bg-white/5 border border-white/10 px-3 text-white/80 text-xs focus:outline-none focus:border-white/30 transition-colors"
            />
          )}
        </div>
      ))}
    </>
  );
};

export default ParamPanel;
