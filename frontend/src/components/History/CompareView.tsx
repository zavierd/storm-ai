import React from 'react';
import { Download, X } from 'lucide-react';
import type { GenerationRecord } from '../../api/projects';

interface CompareViewProps {
  items: GenerationRecord[];
  onClose: () => void;
}

const CompareView: React.FC<CompareViewProps> = ({ items, onClose }) => {
  return (
    <div className="fixed inset-0 z-[120] bg-black/95 p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-white/80 text-sm">多图对比（{items.length} 张）</span>
        <button
          onClick={onClose}
          className="p-2 bg-white/10 hover:bg-white/20 text-white transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-4 overflow-auto">
        {items.map((item) => (
          <div key={item.id} className="border border-white/10 bg-[#161616] p-3 flex flex-col gap-2">
            <div className="aspect-video bg-black/30">
              {item.result_image_url ? (
                <img
                  src={item.result_image_url}
                  alt={item.feature_key}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-white/30 text-xs">
                  无图片
                </div>
              )}
            </div>
            <div className="flex items-center justify-between text-xs text-white/70">
              <span className="truncate">功能：{item.feature_key}</span>
              {item.result_image_url && (
                <button
                  onClick={async () => {
                    try {
                      const res = await fetch(item.result_image_url || '');
                      const blob = await res.blob();
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${item.feature_key}-${item.id}.jpg`;
                      a.click();
                      URL.revokeObjectURL(url);
                    } catch {
                      window.open(item.result_image_url, '_blank');
                    }
                  }}
                  className="flex items-center gap-1 px-2 py-1 bg-white/10 hover:bg-white/20"
                >
                  <Download size={12} />
                  下载
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CompareView;

