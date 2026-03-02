import React, { useEffect, useMemo, useState } from 'react';
import logoWhite from '../assets/logo-white.png';
import BackButton from '../components/ToolList/BackButton';
import UserProfile from '../components/ToolList/UserProfile';
import SideNavBar from '../components/ToolList/SideNavBar';
import { listGenerationHistory, type CreditHistoryRecord } from '../api/history';
import { useAuthStore } from '../stores/useAuthStore';

const PAGE_SIZE = 20;

function formatDateTime(value?: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

function getRecordAmount(record: CreditHistoryRecord): number {
  if (typeof record.amount === 'number' && Number.isFinite(record.amount)) {
    return record.amount;
  }
  if (typeof record.credits_cost === 'number' && Number.isFinite(record.credits_cost)) {
    return -Math.abs(record.credits_cost);
  }
  return 0;
}

const Profile: React.FC = () => {
  const user = useAuthStore((s) => s.user);
  const [showGuides, setShowGuides] = useState(true);
  const [records, setRecords] = useState<CreditHistoryRecord[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async (reset = false) => {
    if (loading) return;
    const currentOffset = reset ? 0 : offset;
    setLoading(true);
    if (reset) setError(null);
    try {
      const nextRecords = await listGenerationHistory(PAGE_SIZE, currentOffset);
      if (reset) {
        setRecords(nextRecords);
      } else {
        setRecords((prev) => [...prev, ...nextRecords]);
      }
      setOffset(currentOffset + nextRecords.length);
      setHasMore(nextRecords.length >= PAGE_SIZE);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载积分历史失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const creditsText = useMemo(
    () => Math.floor(user?.credits_balance ?? 0).toLocaleString('zh-CN'),
    [user?.credits_balance]
  );

  return (
    <div className="h-full">
      {showGuides && (
        <>
          <div className="fixed top-0 bottom-0 left-[120px] w-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed top-0 bottom-0 right-[128px] w-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed left-0 right-0 top-[140px] h-[1px] bg-white/10 z-0 pointer-events-none" />
          <div className="fixed left-0 right-0 bottom-[82px] h-[1px] bg-white/10 z-0 pointer-events-none" />
        </>
      )}

      <button
        onClick={() => setShowGuides(!showGuides)}
        className="fixed bottom-[40px] right-[40px] w-[40px] h-[20px] bg-white/10 hover:bg-white/20 text-white/50 text-[10px] flex items-center justify-center transition-colors z-50"
      >
        {showGuides ? 'HIDE' : 'SHOW'}
      </button>

      <div className="fixed top-[140px] bottom-[82px] left-[120px] right-[128px] flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <span className="text-white/80 text-sm">个人中心</span>
          <span className="text-white/45 text-xs">积分历史</span>
          <button
            onClick={() => loadHistory(true)}
            disabled={loading}
            className="h-9 px-3 bg-white/10 hover:bg-white/20 text-white/70 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            刷新
          </button>
        </div>

        <div className="grid grid-cols-4 gap-3">
          <div className="bg-[#1a1a1a]/80 border border-white/10 px-4 py-3">
            <p className="text-white/40 text-xs">用户名</p>
            <p className="text-white/85 text-sm mt-1 truncate">{user?.username || '-'}</p>
          </div>
          <div className="bg-[#1a1a1a]/80 border border-white/10 px-4 py-3">
            <p className="text-white/40 text-xs">邮箱</p>
            <p className="text-white/85 text-sm mt-1 truncate">{user?.email || '-'}</p>
          </div>
          <div className="bg-[#1a1a1a]/80 border border-white/10 px-4 py-3">
            <p className="text-white/40 text-xs">当前积分</p>
            <p className="text-[#E2E85C] text-sm mt-1">{creditsText}</p>
          </div>
          <div className="bg-[#1a1a1a]/80 border border-white/10 px-4 py-3">
            <p className="text-white/40 text-xs">注册时间</p>
            <p className="text-white/85 text-sm mt-1 truncate">{formatDateTime(user?.created_at)}</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/30 px-3 py-2 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
          {records.length > 0 && (
            <div className="bg-[#1a1a1a]/80 border border-white/10 overflow-hidden">
              <div className="grid grid-cols-[1fr_160px_160px] px-4 py-2 border-b border-white/10 text-[11px] text-white/45">
                <span>说明</span>
                <span>积分变化</span>
                <span>时间</span>
              </div>
              {records.map((item) => {
                const amount = getRecordAmount(item);
                const amountText = `${amount > 0 ? '+' : ''}${amount.toLocaleString('zh-CN')}`;
                return (
                  <div
                    key={item.id}
                    className="grid grid-cols-[1fr_160px_160px] px-4 py-3 border-b border-white/5 last:border-b-0"
                  >
                    <div className="min-w-0">
                      <p className="text-white/80 text-sm truncate">
                        {item.reason || item.prompt_text || item.feature_key || '积分变动'}
                      </p>
                      <p className="text-white/35 text-xs truncate mt-1">
                        功能标识：{item.feature_key || '-'}
                      </p>
                    </div>
                    <span
                      className={`text-sm ${
                        amount > 0 ? 'text-emerald-300' : amount < 0 ? 'text-[#E2E85C]' : 'text-white/55'
                      }`}
                    >
                      {amountText}
                    </span>
                    <span className="text-white/45 text-xs">{formatDateTime(item.created_at)}</span>
                  </div>
                );
              })}
            </div>
          )}

          {!loading && !error && records.length === 0 && (
            <div className="h-full min-h-[220px] flex items-center justify-center bg-[#1a1a1a]/40 border border-white/10 text-white/45 text-sm">
              暂无积分历史记录
            </div>
          )}

          {loading && (
            <div className="py-6 text-white/50 text-sm">
              {records.length === 0 ? '加载中...' : '正在加载更多...'}
            </div>
          )}

          {hasMore && !error && (
            <div className="py-6">
              <button
                onClick={() => loadHistory(false)}
                disabled={loading}
                className="h-9 px-5 bg-white/10 hover:bg-white/20 text-white/75 text-sm disabled:opacity-40"
              >
                {loading ? '加载中...' : '加载更多'}
              </button>
            </div>
          )}
        </div>
      </div>

      <BackButton />
      <SideNavBar />
      <UserProfile />

      <div className="fixed top-[60px] left-[120px] w-[220px] h-[20px] flex items-center justify-center z-0 pointer-events-none">
        <span
          className="text-white font-handwriting drop-shadow-lg"
          style={{ fontFamily: "'Pinyon Script', cursive", fontSize: '4rem', marginBottom: '13px', opacity: 0.1 }}
        >
          design
        </span>
      </div>
      <div className="fixed top-[80px] left-[120px] w-[220px] h-[20px] flex items-center justify-start z-50">
        <img src={logoWhite} alt="Logo" className="h-full w-auto object-contain opacity-90" />
      </div>
    </div>
  );
};

export default Profile;
