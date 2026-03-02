import React, { useRef, useState } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
}

const UploadZone: React.FC<UploadZoneProps> = ({ onFileSelect }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        handleFile(file);
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file: File) => {
    onFileSelect(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const clearImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (preview) {
    return (
      <div className="w-full h-full relative group overflow-hidden border border-white/10">
        <img src={preview} alt="Preview" className="w-full h-full object-cover" />
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button 
            onClick={clearImage}
            className="p-2 bg-white/10 hover:bg-[#E2E85C] text-white hover:text-black rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`w-full h-full border border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-200 group
        ${isDragging ? 'border-[#E2E85C] bg-white/5' : 'border-white/20 hover:border-white/40 hover:bg-white/5'}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input 
        type="file" 
        ref={fileInputRef}
        className="hidden" 
        accept="image/*"
        onChange={handleFileChange}
      />
      <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 transition-colors duration-200
        ${isDragging ? 'bg-[#E2E85C]/20 text-[#E2E85C]' : 'bg-white/5 text-white/40 group-hover:bg-white/10 group-hover:text-white/60'}`}>
        <Upload size={24} strokeWidth={1.5} />
      </div>
      <span className={`text-sm font-light transition-colors duration-200
        ${isDragging ? 'text-[#E2E85C]' : 'text-white/40 group-hover:text-white/60'}`}>
        点击或拖拽上传草图大师方案
      </span>
      <span className="text-xs text-white/20 mt-2 font-light">
        支持 JPG, PNG, WEBP
      </span>
    </div>
  );
};

export default UploadZone;
