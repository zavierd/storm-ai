import React from 'react';
import Logo from '../components/Home/Logo';
import EnterButton from '../components/Home/EnterButton';
import DesignText from '../components/Home/DesignText';

const Home: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center h-screen w-screen relative overflow-hidden" style={{ backgroundColor: '#E2E85C' }}>
      
      {/* Grid Background - Fixed Position */}
      <div 
        className="absolute inset-0 pointer-events-none" 
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(0, 0, 0, 0.05) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.05) 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
          backgroundPosition: 'center center' // Ensure grid is centered
        }}
      />
      
      <DesignText />
      <Logo />
      <EnterButton />
      
    </div>
  );
};

export default Home;