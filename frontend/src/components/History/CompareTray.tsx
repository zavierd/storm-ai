import React from 'react';

interface CompareTrayProps {
  selectedCount: number;
  max: number;
  onClear: () => void;
  onCompare: () => void;
}

const CompareTray: React.FC<CompareTrayProps> = ({
  selectedCount,
  max,
  onClear,
  onCompare,
}) => {
  if (selectedCount === 0) return null;
  return (
    <div className="fixed bottom-[92px] left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-4 py-3 bg-black/80 border border-white/15">
      <span className="text-white/80 text-sm">
        已选择 {selectedCount}/{max} 张
      </span>
      <button
        onClick={onClear}
        className="h-8 px-3 bg-white/10 hover:bg-white/20 text-white/75 text-xs"
      >
        清空
      </button>
      <button
        onClick={onCompare}
        className="h-8 px-4 bg-[#E2E85C] text-black text-xs"
      >
        开始对比
      </button>
    </div>
  );
};

export default CompareTray;

