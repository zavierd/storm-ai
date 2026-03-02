import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Upload, X, Clipboard } from 'lucide-react';

interface UploadZoneProps {
  label: string;
  hint: string;
  onFileSelect: (file: File) => void;
  onClear?: () => void;
}

const UploadZone: React.FC<UploadZoneProps> = ({ label, hint, onFileSelect, onClear }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [pasteHint, setPasteHint] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleFile = useCallback((file: File) => {
    onFileSelect(file);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);
  }, [onFileSelect]);

  // 全局剪贴板粘贴监听
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) handleFile(file);
          return;
        }
      }
    };
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [handleFile]);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]?.type.startsWith('image/')) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const clearImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onClear?.();
  };

  if (preview) {
    return (
      <div className="w-full h-full relative group overflow-hidden border border-white/10">
        <img src={preview} alt="Preview" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button onClick={clearImage} className="p-2 bg-white/10 hover:bg-[#E2E85C] text-white hover:text-black rounded-full transition-colors">
            <X size={20} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`w-full h-full border border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-200 group
        ${isDragging ? 'border-[#E2E85C] bg-white/5' : 'border-white/20 hover:border-white/40 hover:bg-white/5'}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      onMouseEnter={() => setPasteHint(true)}
      onMouseLeave={() => setPasteHint(false)}
    >
      <input type="file" ref={fileInputRef} className="hidden" accept="image/*"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />

      <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 transition-colors duration-200
        ${isDragging ? 'bg-[#E2E85C]/20 text-[#E2E85C]' : 'bg-white/5 text-white/40 group-hover:bg-white/10 group-hover:text-white/60'}`}>
        <Upload size={24} strokeWidth={1.5} />
      </div>

      <span className={`text-sm font-light transition-colors duration-200
        ${isDragging ? 'text-[#E2E85C]' : 'text-white/40 group-hover:text-white/60'}`}>
        {label}
      </span>

      <span className="text-xs text-white/20 mt-2 font-light">{hint}</span>

      <div className={`flex items-center gap-1 mt-3 transition-opacity duration-200 ${pasteHint ? 'opacity-100' : 'opacity-0'}`}>
        <Clipboard size={12} className="text-[#E2E85C]/60" />
        <span className="text-xs text-[#E2E85C]/60">Ctrl+V 粘贴截图</span>
      </div>
    </div>
  );
};

export default UploadZone;
