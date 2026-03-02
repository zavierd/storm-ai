import React from 'react';
import { Cpu, LogOut, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';

const UserProfile: React.FC = () => {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  if (!user) return null;

  const initial = user.username?.charAt(0).toUpperCase() || '?';
  const creditsBalance =
    typeof user.credits_balance === 'number' && Number.isFinite(user.credits_balance) ? user.credits_balance : 0;
  const credits = Math.floor(creditsBalance).toLocaleString('zh-CN');

  return (
    <div className="fixed top-[60px] right-[128px] flex items-center gap-5 z-50">
      <button
        onClick={() => navigate('/profile')}
        className="flex items-center justify-between h-[40px] px-3 bg-white/10 hover:bg-white/20 transition-colors duration-200 w-[100px]"
      >
        <Cpu className="w-4 h-4 text-green-400" />
        <span className="text-white font-light text-sm tracking-wider">{credits}</span>
      </button>

      <div className="relative group">
        <button className="w-[40px] h-[40px] bg-white/10 hover:bg-white/20 transition-colors duration-200 flex items-center justify-center overflow-hidden">
          <span className="text-white font-light text-lg">{initial}</span>
        </button>
        <div className="absolute right-0 top-full w-[160px] bg-[#2a2a2a]/90 backdrop-blur-md border border-white/10 rounded-lg shadow-xl overflow-hidden py-1 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity z-50">
          <div className="px-4 py-2 border-b border-white/10">
            <p className="text-white text-sm">{user.username}</p>
            <p className="text-white/40 text-xs truncate">{user.email}</p>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="w-full text-left px-4 py-2 text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors flex items-center gap-2"
          >
            <User size={14} /> 个人中心
          </button>
          <button
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full text-left px-4 py-2 text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors flex items-center gap-2"
          >
            <LogOut size={14} /> 退出登录
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
