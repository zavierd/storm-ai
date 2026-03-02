import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { X } from 'lucide-react';
import logoWhite from '../assets/logo-white.png';
import BackButton from '../components/ToolList/BackButton';
import UserProfile from '../components/ToolList/UserProfile';
import SideNavBar from '../components/ToolList/SideNavBar';
import CompareTray from '../components/History/CompareTray';
import CompareView from '../components/History/CompareView';
import {
  listProjectGenerations,
  type GenerationRecord,
  type ProjectRecord,
  updateProjectName,
} from '../api/projects';

const PAGE_SIZE = 20;
const MAX_COMPARE = 4;

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [showGuides, setShowGuides] = useState(true);
  const [project, setProject] = useState<ProjectRecord | null>(null);
  const [records, setRecords] = useState<GenerationRecord[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [savingName, setSavingName] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);

  const loadRecords = async (reset = false) => {
    if (!id || loading) return;
    const currentOffset = reset ? 0 : offset;
    setLoading(true);
    setError(null);
    try {
      const data = await listProjectGenerations(id, PAGE_SIZE, currentOffset);
      setProject(data.project);
      setEditingName((prev) => prev || data.project.name || '');
      if (reset) {
        setRecords(data.records);
      } else {
        setRecords((prev) => [...prev, ...data.records]);
      }
      setOffset(currentOffset + data.records.length);
      setHasMore(data.records.length >= PAGE_SIZE);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载项目内容失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleRename = async () => {
    if (!id || !editingName.trim() || !project) return;
    setSavingName(true);
    setError(null);
    try {
      const record = await updateProjectName(id, editingName.trim());
      setProject((prev) => (prev ? { ...prev, name: record.name } : prev));
      setEditingName(record.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : '重命名失败');
    } finally {
      setSavingName(false);
    }
  };

  const toggleSelect = (recordId: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(recordId)) return prev.filter((id2) => id2 !== recordId);
      if (prev.length >= MAX_COMPARE) return prev;
      return [...prev, recordId];
    });
  };

  const selectedRecords = records.filter((r) => selectedIds.includes(r.id));

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
          <button
            onClick={() => navigate('/projects')}
            className="h-9 px-3 bg-white/10 hover:bg-white/20 text-white/80 text-sm"
          >
            返回项目列表
          </button>
          <input
            value={editingName}
            onChange={(e) => setEditingName(e.target.value)}
            className="w-[260px] h-9 bg-white/5 border border-white/10 px-3 text-white/85 text-sm focus:outline-none focus:border-white/30"
          />
          <button
            onClick={handleRename}
            disabled={savingName || !editingName.trim()}
            className="h-9 px-4 bg-[#E2E85C] text-black text-sm disabled:opacity-40"
          >
            {savingName ? '保存中...' : '重命名'}
          </button>
          <button
            onClick={() => loadRecords(true)}
            className="h-9 px-3 bg-white/10 hover:bg-white/20 text-white/70 text-sm"
          >
            刷新
          </button>
          <span className="text-white/45 text-xs">最多选择 {MAX_COMPARE} 张进行对比</span>
          <span className="text-white/45 text-xs">
            {project?.image_count || records.length} 张图片
          </span>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/30 px-3 py-2 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="grid grid-cols-3 gap-4">
            {records.map((item) => (
              <div key={item.id} className="bg-[#1a1a1a]/80 border border-white/10 overflow-hidden">
                <div className="aspect-video bg-black/20 relative">
                  <label className="absolute mt-2 ml-2 z-10 bg-black/60 px-2 py-1 text-[11px] text-white/85 flex items-center gap-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(item.id)}
                      onChange={() => toggleSelect(item.id)}
                      disabled={!selectedIds.includes(item.id) && selectedIds.length >= MAX_COMPARE}
                      className="accent-[#E2E85C]"
                    />
                    对比
                  </label>
                  {item.result_image_url ? (
                    <img
                      src={item.result_image_url}
                      alt={item.feature_key}
                      className="w-full h-full object-cover cursor-zoom-in"
                      onClick={() => setPreview(item.result_image_url || null)}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white/25 text-xs">
                      无图片URL
                    </div>
                  )}
                </div>
                <div className="p-3 text-xs text-white/70 space-y-1">
                  <div className="truncate">功能：{item.feature_key}</div>
                  <div className="truncate">房间：{item.room_type || '-'}</div>
                  <div className="truncate">时间：{item.created_at || '-'}</div>
                </div>
              </div>
            ))}
          </div>

          {hasMore && (
            <div className="py-6">
              <button
                onClick={() => loadRecords(false)}
                disabled={loading}
                className="h-9 px-5 bg-white/10 hover:bg-white/20 text-white/75 text-sm disabled:opacity-40"
              >
                {loading ? '加载中...' : '加载更多'}
              </button>
            </div>
          )}
        </div>
      </div>

      {preview && (
        <div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center cursor-zoom-out"
          onClick={() => setPreview(null)}
        >
          <img
            src={preview}
            alt="Preview"
            className="max-w-[95vw] max-h-[95vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setPreview(null)}
            className="absolute top-6 right-6 p-2 bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X size={24} strokeWidth={1.5} />
          </button>
        </div>
      )}

      <CompareTray
        selectedCount={selectedIds.length}
        max={MAX_COMPARE}
        onClear={() => setSelectedIds([])}
        onCompare={() => setCompareOpen(true)}
      />
      {compareOpen && selectedRecords.length > 0 && (
        <CompareView
          items={selectedRecords}
          onClose={() => setCompareOpen(false)}
        />
      )}

      <BackButton />
      <SideNavBar />
      <UserProfile />

      <div className="fixed top-[60px] left-[120px] w-[220px] h-[20px] flex items-center justify-center z-0 pointer-events-none">
        <span className="text-white font-handwriting drop-shadow-lg" style={{ fontFamily: "'Pinyon Script', cursive", fontSize: '4rem', marginBottom: '13px', opacity: 0.1 }}>
          design
        </span>
      </div>
      <div className="fixed top-[80px] left-[120px] w-[220px] h-[20px] flex items-center justify-start z-50">
        <img src={logoWhite} alt="Logo" className="h-full w-auto object-contain opacity-90" />
      </div>
    </div>
  );
};

export default ProjectDetail;

