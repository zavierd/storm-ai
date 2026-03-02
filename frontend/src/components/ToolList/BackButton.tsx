import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

function getBackTarget(pathname: string): string | null {
  if (pathname === '/tools' || pathname === '/') return null;
  if (/^\/tools\/[^/]+/.test(pathname)) return '/tools';
  if (/^\/projects\/[^/]+/.test(pathname)) return '/projects';
  if (pathname === '/projects') return '/tools';
  if (pathname === '/profile') return '/tools';
  return null;
}

const BackButton: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const backTarget = getBackTarget(location.pathname);
  const active = backTarget !== null;

  return (
    <div className="fixed top-[60px] left-0 w-[120px] h-[20px] flex items-center justify-center z-50 pointer-events-none">
      <button 
        onClick={active ? () => navigate(backTarget) : undefined}
        className={`w-full h-full flex items-center justify-center bg-white/10 text-white font-light text-sm pointer-events-auto
          ${active ? 'hover:bg-[#E2E85C] hover:text-black transition-colors duration-200 cursor-pointer' : 'cursor-default'}`}
      >
        back
      </button>
    </div>
  );
};

export default BackButton;
