import React from 'react';
import { Home, Image, Zap, User, LayoutGrid } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

const SideNavBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { icon: Home, label: '首页', path: '/' },
    { icon: LayoutGrid, label: '工具', path: '/tools' },
    { icon: Image, label: '图库', path: '/projects' },
    { icon: Zap, label: '算力', path: '/tools' },
    { icon: User, label: '个人中心', path: '/profile' },
  ];

  return (
    <div className="fixed top-[140px] bottom-[82px] left-[30px] w-[60px] z-40 flex flex-col justify-center pointer-events-none">
      <div className="w-full h-[340px] flex flex-col items-center justify-between py-6 bg-white/10 pointer-events-auto opacity-0 hover:opacity-100 transition-opacity duration-300">
        {navItems.map((item, index) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={index}
              onClick={() => navigate(item.path)}
              className={`w-10 h-10 flex items-center justify-center transition-all duration-200 group relative ${
                isActive
                  ? 'text-[#E2E85C] bg-white/5'
                  : 'text-white/60 hover:text-[#E2E85C] hover:bg-white/5'
              }`}
            >
              <item.icon size={20} strokeWidth={1.5} />
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SideNavBar;
