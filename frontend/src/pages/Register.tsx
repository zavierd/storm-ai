import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';

const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const register = useAuthStore((s) => s.register);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !email || !password) { setError('请填写所有字段'); return; }
    if (password !== confirm) { setError('两次密码不一致'); return; }
    if (password.length < 6) { setError('密码至少6位'); return; }
    setLoading(true);
    setError(null);
    const err = await register(username, email, password);
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
        <h1 className="text-white text-lg tracking-wider text-center mb-2">注册</h1>

        {error && <div className="bg-red-500/20 border border-red-500/30 px-4 py-2 text-red-300 text-xs">{error}</div>}

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">用户名</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="2-50个字符" />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">邮箱</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="your@email.com" />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">密码</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="至少6位" />
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-white/60 text-xs">确认密码</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)}
            className="h-10 bg-white/5 border border-white/10 px-4 text-white text-sm focus:outline-none focus:border-[#E2E85C]/50 transition-colors"
            placeholder="再次输入密码" />
        </div>

        <button type="submit" disabled={loading}
          className="h-10 bg-[#E2E85C] text-black text-sm font-medium opacity-80 hover:opacity-100 disabled:opacity-30 flex items-center justify-center gap-2 transition-all">
          {loading ? <><Loader2 size={16} className="animate-spin" /> 注册中...</> : '注册'}
        </button>

        <p className="text-white/40 text-xs text-center">
          已有账号？<Link to="/login" className="text-[#E2E85C]/80 hover:text-[#E2E85C]">登录</Link>
        </p>

        <p className="text-white/30 text-xs text-center">注册即赠送 1000 算力</p>
      </form>
    </div>
  );
};

export default Register;
