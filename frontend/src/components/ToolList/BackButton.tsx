import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const BackButton: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isToolsPage = location.pathname === '/tools';

  const handleBack = () => {
    if (isToolsPage) {
      navigate('/');
    }
  };

  return (
    <div className="fixed top-[60px] left-0 w-[120px] h-[20px] flex items-center justify-center z-50 pointer-events-none">
      <button 
        onClick={isToolsPage ? handleBack : undefined}
        className={`w-full h-full flex items-center justify-center bg-white/10 text-white font-light text-sm pointer-events-auto
          ${isToolsPage ? 'hover:bg-[#E2E85C] hover:text-black transition-colors duration-200 cursor-pointer' : 'cursor-default'}`}
      >
        back
      </button>
    </div>
  );
};

export default BackButton;
