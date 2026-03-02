import React from 'react';

const DesignText: React.FC = () => {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-0 pointer-events-none">
      <span 
        className="text-white font-handwriting opacity-50 drop-shadow-lg" 
        style={{ 
          fontFamily: "'Pinyon Script', cursive",
          fontSize: '12rem',
          marginBottom: '40px', // Adjusted: 60px - 20px (1 grid) = 40px
        }}
      >
        design
      </span>
    </div>
  );
};

export default DesignText;