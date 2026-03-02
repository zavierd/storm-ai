import React from 'react';
import { Link } from 'react-router-dom';

const EnterButton: React.FC = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
      <div className="pointer-events-auto mt-[140px]"> {/* 140px = 7 grids (20px * 7) */}
        <Link 
          to="/tools" 
          className="h-[40px] flex items-center justify-center bg-black/10 text-black font-light text-lg hover:bg-black/20 transition"
          style={{
            width: '220px', // 11 grids wide (20px * 11)
          }}
        >
          enter
        </Link>
      </div>
    </div>
  );
};

export default EnterButton;