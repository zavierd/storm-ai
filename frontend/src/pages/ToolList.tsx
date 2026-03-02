import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logoWhite from '../assets/logo-white.png';
import BackButton from '../components/ToolList/BackButton';
import UserProfile from '../components/ToolList/UserProfile';
import SideNavBar from '../components/ToolList/SideNavBar';
import { toolConfigs } from '../config/toolConfigs';

const ToolList: React.FC = () => {
  const [showGuides, setShowGuides] = useState(true);
  const navigate = useNavigate();

  return (
    <div className="h-full">
      {/* Auxiliary Lines */}
      {showGuides && (
        <>
          <div className="fixed top-0 bottom-0 left-[120px] w-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed top-0 bottom-0 right-[128px] w-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed left-0 right-0 top-[140px] h-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed left-0 right-0 bottom-[82px] h-[1px] bg-white/10 z-0 pointer-events-none" />
        </>
      )}

      <button
        onClick={() => setShowGuides(!showGuides)}
        className="fixed bottom-[40px] right-[40px] w-[40px] h-[20px] bg-white/10 hover:bg-white/20 text-white/50 text-[10px] flex items-center justify-center transition-colors z-50"
      >
        {showGuides ? 'HIDE' : 'SHOW'}
      </button>

      {/* Card Grid */}
      <div className="fixed top-[140px] bottom-[82px] left-[120px] right-[128px] overflow-y-auto pr-0">
        <div className="flex flex-wrap gap-[20px]">
          {toolConfigs.map((tool) => (
            <div
              key={tool.id}
              onClick={() => navigate(`/tools/${tool.slug}`)}
              className="w-[280px] h-[220px] bg-[#1a1a1a]/80 hover:bg-[#E2E85C] hover:text-black transition-colors flex flex-col cursor-pointer duration-200 overflow-hidden group"
            >
              <div className="h-[60px] flex items-center px-4 border-b border-white/10 group-hover:border-black/10">
                <span className="text-white/80 group-hover:text-black text-sm tracking-wider transition-colors">
                  {tool.title}
                </span>
              </div>
              <div className="h-[160px] w-full relative overflow-hidden bg-black/20">
                <img
                  src={tool.image}
                  alt={tool.title}
                  className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity duration-200"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <BackButton />
      <SideNavBar />
      <UserProfile />

      {/* Watermark */}
      <div className="fixed top-[60px] left-[120px] w-[220px] h-[20px] flex items-center justify-center z-0 pointer-events-none">
        <span className="text-white font-handwriting drop-shadow-lg" style={{ fontFamily: "'Pinyon Script', cursive", fontSize: '4rem', marginBottom: '13px', opacity: 0.1 }}>
          design
        </span>
      </div>

      {/* Logo */}
      <div className="fixed top-[80px] left-[120px] w-[220px] h-[20px] flex items-center justify-start z-50">
        <img src={logoWhite} alt="Logo" className="h-full w-auto object-contain opacity-90" />
      </div>
    </div>
  );
};

export default ToolList;
