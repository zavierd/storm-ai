import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logoWhite from '../assets/logo-white.png';
import BackButton from '../components/ToolList/BackButton';
import UserProfile from '../components/ToolList/UserProfile';
import SideNavBar from '../components/ToolList/SideNavBar';
import { createProject, listProjects, type ProjectRecord } from '../api/projects';

const PAGE_SIZE = 20;

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [showGuides, setShowGuides] = useState(true);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const loadProjects = async (reset = false) => {
    const currentOffset = reset ? 0 : offset;
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const records = await listProjects(PAGE_SIZE, currentOffset);
      if (reset) {
        setProjects(records);
      } else {
        setProjects((prev) => [...prev, ...records]);
      }
      setOffset(currentOffset + records.length);
      setHasMore(records.length >= PAGE_SIZE);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    setError(null);
    try {
      const record = await createProject(name);
      setProjects((prev) => [record, ...prev]);
      setNewName('');
      navigate(`/projects/${record.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建项目失败');
    } finally {
      setCreating(false);
    }
  };

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
          <span className="text-white/80 text-sm">我的项目</span>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="输入新项目名"
            className="w-[220px] h-9 bg-white/5 border border-white/10 px-3 text-white/80 text-sm focus:outline-none focus:border-white/30"
          />
          <button
            onClick={handleCreate}
            disabled={creating || !newName.trim()}
            className="h-9 px-4 bg-[#E2E85C] text-black text-sm disabled:opacity-40"
          >
            {creating ? '创建中...' : '新建项目'}
          </button>
          <button
            onClick={() => loadProjects(true)}
            className="h-9 px-3 bg-white/10 hover:bg-white/20 text-white/70 text-sm"
          >
            刷新
          </button>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500/30 px-3 py-2 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="flex flex-wrap gap-[20px]">
            {projects.map((project) => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="w-[280px] h-[220px] bg-[#1a1a1a]/80 hover:bg-[#E2E85C] hover:text-black transition-colors flex flex-col cursor-pointer duration-200 overflow-hidden group"
              >
                <div className="h-[70px] flex flex-col justify-center px-4 border-b border-white/10 group-hover:border-black/10">
                  <span className="text-white/85 group-hover:text-black text-sm tracking-wider transition-colors truncate">
                    {project.name}
                  </span>
                  <span className="text-white/45 group-hover:text-black/70 text-xs mt-1 transition-colors">
                    {project.image_count || 0} 张图片
                  </span>
                </div>
                <div className="h-[150px] w-full relative overflow-hidden bg-black/20">
                  {project.cover_image_url ? (
                    <img
                      src={project.cover_image_url}
                      alt={project.name}
                      className="w-full h-full object-cover opacity-65 group-hover:opacity-100 transition-opacity duration-200"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white/30 text-sm group-hover:text-black/60 transition-colors">
                      暂无封面
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {hasMore && (
            <div className="py-6">
              <button
                onClick={() => loadProjects(false)}
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

export default Projects;

