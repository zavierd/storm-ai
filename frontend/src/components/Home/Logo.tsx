import React from 'react';
import logo from '../../assets/logo.png';

const Logo: React.FC = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
      <img 
        src={logo} 
        alt="Logo" 
        className="w-2/3 md:w-1/3 max-w-lg object-contain"
        style={{ 
          filter: 'grayscale(100%) contrast(150%) opacity(0.9)', 
          mixBlendMode: 'multiply' 
        }} 
      />
    </div>
  );
};

export default Logo;