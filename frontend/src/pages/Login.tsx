import React, { useState } from 'react';
import { useNavigate, Link, Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  if (isAuthenticated) return <Navigate to="/tools" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) { setError('请填写用户名和密码'); return; }
    setLoading(true);
    setError(null);
    const err = await login(username, password);
    setLoading(false);
    if (err) { setError(err); } else { navigate('/tools'); }
  };

  return (
    <div className="flex items-center justify-center h-screen w-screen bg-black relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" style={{
        backgroundImage: 'linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)',
        backgroundSize: '20px 20px',
      }} />

      <form onSubmit={handleSubmit} className="relative z-10 w-[360px] bg-[#1a1a1a]/80 border border-white/10 p-8 flex flex-col gap-5">
        <h1 className="text-white text-lg tracking-wider text-center mb-2">登录</h1>

        {error && <div className="bg-red-500/20 border border-red-500/30 px-4 py-2 text-red-300 text-xs">{error}</div>}

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">用户名 / 邮箱</label>
          <input
            type="text" value={username} onChange={(e) => setUsername(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="输入用户名或邮箱"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">密码</label>
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="输入密码"
          />
        </div>

        <button
          type="submit" disabled={loading}
          className="h-10 bg-[#E2E85C] text-black text-sm font-medium opacity-80 hover:opacity-100 disabled:opacity-30 flex items-center justify-center gap-2 transition-all"
        >
          {loading ? <><Loader2 size={16} className="animate-spin" /> 登录中...</> : '登录'}
        </button>

        <p className="text-white/40 text-xs text-center">
          没有账号？<Link to="/register" className="text-[#E2E85C]/80 hover:text-[#E2E85C]">注册</Link>
        </p>
      </form>
    </div>
  );
};

export default Login;
