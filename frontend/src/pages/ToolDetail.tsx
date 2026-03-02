import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { X, Zap, ChevronDown, Download, Loader2, ZoomIn } from 'lucide-react';
import logoWhite from '../assets/logo-white.png';
import BackButton from '../components/ToolList/BackButton';
import UserProfile from '../components/ToolList/UserProfile';
import SideNavBar from '../components/ToolList/SideNavBar';
import UploadZone from '../components/ToolDetail/UploadZone';
import ParamPanel from '../components/ToolDetail/ParamPanel';
import RoomSelector from '../components/ToolDetail/RoomSelector';
import RegionCanvas from '../components/ToolDetail/RegionCanvas';
import type { RegionData } from '../components/ToolDetail/RegionCanvas';
import {
  toolConfigs,
  getToolBySlug,
  getResolutionsByChannel,
  getResolutionCost,
  aspectRatios,
  type ToolConfig,
} from '../config/toolConfigs';
import { generateImage, type GenerateParams } from '../api/generate';
import { getDefaultEngineType } from '../api/engines';
import { listProjects, type ProjectRecord } from '../api/projects';
import { useAuthStore } from '../stores/useAuthStore';

const FRIENDLY_ERROR_MESSAGE: Record<string, string> = {
  CONTENT_BLOCKED_IMAGE:
    '本次生成触发了内容安全策略，返回占位图已被系统拦截。请调整提示词后重试（建议明确“成年/成人人物”，避免敏感或歧义描述）。',
};

const REGION_REQUIRED_FEATURES = new Set([
  'partial-replace',
  'material-replace',
  'local-lighting',
]);

const ToolDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();

  const tool = getToolBySlug(slug || '');

  const [showGuides, setShowGuides] = useState(true);
  const [selectedResolution, setSelectedResolution] = useState('1080p');
  const [selectedRatio, setSelectedRatio] = useState('default');
  const [showToolMenu, setShowToolMenu] = useState(false);
  const [promptText, setPromptText] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [secondImageFile, setSecondImageFile] = useState<File | null>(null);
  const [secondImageBase64, setSecondImageBase64] = useState<string | null>(null);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, string | number | boolean>>({});
  const [roomType, setRoomType] = useState('living_room');
  const [showPreview, setShowPreview] = useState(false);
  const [regionData, setRegionData] = useState<RegionData | null>(null);
  const [layoutStrict, setLayoutStrict] = useState(false);
  const [skipTranslation, setSkipTranslation] = useState(false);
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [projectLoadError, setProjectLoadError] = useState<string | null>(null);
  const [defaultEngineType, setDefaultEngineType] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const updateCredits = useAuthStore((s) => s.updateCredits);

  /** 分辨率按工具能力显示；默认 1080p。 */
  const isImageDrivenTool = !!tool && (tool.requiresImage !== false || tool.hasDualImage);
  const availableResolutions = useMemo(
    () => (tool ? getResolutionsByChannel(tool, defaultEngineType) : []),
    [tool, defaultEngineType]
  );
  const showP0Switches = isImageDrivenTool && tool?.outputType !== 'text';
  const resolutionEnabled = availableResolutions.length > 0;
  const aspectRatioEnabled = !!tool && tool.hasAspectRatio && !isImageDrivenTool;
  const requiresRegionForGenerate = !!tool && REGION_REQUIRED_FEATURES.has(tool.featureKey);
  const displayCost = tool
    ? (resolutionEnabled ? getResolutionCost(tool.costPerGeneration, selectedResolution) : tool.costPerGeneration)
    : 0;

  useEffect(() => {
    if (tool) {
      const defaults: Record<string, string | number | boolean> = {};
      tool.customParams.forEach((p) => { defaults[p.key] = p.defaultValue; });
      setParamValues(defaults);
      const nextResolution = availableResolutions.some((r) => r.value === '1080p')
        ? '1080p'
        : (availableResolutions[0]?.value ?? '1080p');
      setSelectedResolution(nextResolution);
    }
  }, [tool, availableResolutions]);

  useEffect(() => {
    let alive = true;
    const loadProjects = async () => {
      try {
        const records = await listProjects(50, 0);
        if (!alive) return;
        setProjects(records);
        if (!selectedProjectId && records.length > 0) {
          setSelectedProjectId(records[0].id);
        }
      } catch (e) {
        if (!alive) return;
        setProjectLoadError(e instanceof Error ? e.message : '加载项目失败');
      }
    };
    loadProjects();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    const loadEngineType = async () => {
      try {
        const engineType = await getDefaultEngineType();
        if (!alive) return;
        setDefaultEngineType(engineType);
      } catch {
        if (!alive) return;
        setDefaultEngineType(null);
      }
    };
    loadEngineType();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (showToolMenu && !(e.target as HTMLElement).closest('.tool-menu-container')) {
        setShowToolMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showToolMenu]);

  const handleFileSelect = useCallback((file: File) => {
    setImageFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1];
      setImageBase64(base64);
    };
    reader.readAsDataURL(file);
  }, []);

  useEffect(() => {
    if (!imageBase64) setRegionData(null);
  }, [imageBase64]);

  const handleSecondFileSelect = useCallback((file: File) => {
    setSecondImageFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result as string).split(',')[1];
      setSecondImageBase64(base64);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleGenerate = async () => {
    if (!tool) return;
    setIsGenerating(true);
    setError(null);
    setResultImage(null);
    setResultText(null);

    const normalizedPrompt = promptText.trim();
    const featurePromptParams: Record<string, string | number | boolean> = {};
    if (normalizedPrompt) {
      switch (tool.featureKey) {
        case 'local-material-change':
          featurePromptParams.new_material = normalizedPrompt;
          break;
        case 'material-replace':
          featurePromptParams.target_material = normalizedPrompt;
          break;
        case 'partial-replace':
          featurePromptParams.replace_description = normalizedPrompt;
          break;
        case 'locked-material-render':
          featurePromptParams.material_description = normalizedPrompt;
          break;
        default:
          break;
      }
    }
    if (tool.featureKey === 'universal-edit') {
      featurePromptParams.has_person_reference = !!secondImageBase64;
    }

    const params: GenerateParams = {
      featureKey: tool.featureKey,
      projectId: selectedProjectId || undefined,
      imageBase64: imageBase64 || undefined,
      secondImageBase64: tool.hasDualImage ? (secondImageBase64 || undefined) : undefined,
      promptText: promptText || undefined,
      resolution: resolutionEnabled ? selectedResolution : undefined,
      aspectRatio: aspectRatioEnabled ? selectedRatio : undefined,
      region: tool.hasRegion ? regionData : undefined,
      layoutStrict: showP0Switches ? layoutStrict : undefined,
      skipTranslation: showP0Switches ? skipTranslation : undefined,
      extraParams: {
        ...paramValues,
        ...(tool.hasRoomSelect ? { room_type: roomType } : {}),
        ...featurePromptParams,
      },
    };

    try {
      const result = await generateImage(tool, params);
      if (result.success) {
        if (result.imageUrl) {
          setResultImage(result.imageUrl);
        } else if (result.imageBase64) {
          setResultImage(result.imageBase64);
        }
        if (result.text) {
          setResultText(result.text);
        }
        if (!result.imageUrl && !result.imageBase64 && !result.text) {
          setResultText('生成完成但未返回图片，请检查后端日志');
        }
      } else {
        setError(
          (result.errorCode ? FRIENDLY_ERROR_MESSAGE[result.errorCode] : undefined)
            || result.error
            || '生成失败'
        );
      }
    } catch {
      setError('生成过程中发生错误');
    } finally {
      setIsGenerating(false);
    }
  };

  if (!tool) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="text-white/40">工具未找到</span>
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* Auxiliary Lines */}
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

      {/* Main Content */}
      <div className="fixed top-[140px] bottom-[82px] left-[120px] right-[128px] bg-[#1a1a1a]/80 z-10 flex flex-col border border-white/10">
        {/* Title Bar */}
        <div className="h-[60px] flex items-center justify-between px-6 border-b border-white/10 relative z-50 bg-[#1a1a1a]">
          <div className="flex items-center gap-2 relative tool-menu-container">
            <button
              onClick={() => setShowToolMenu(!showToolMenu)}
              className="flex items-center gap-2 text-white/80 text-sm tracking-wider hover:text-white transition-colors"
            >
              {tool.title}
              <ChevronDown size={14} className={`text-white/40 transition-transform duration-200 ${showToolMenu ? 'rotate-180' : ''}`} />
            </button>

            {showToolMenu && (
              <div className="absolute top-full left-0 mt-2 w-[240px] bg-[#2a2a2a]/60 backdrop-blur-md border border-white/10 rounded-lg shadow-xl overflow-hidden py-1 max-h-[400px] overflow-y-auto z-50">
                {toolConfigs.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => {
                      setShowToolMenu(false);
                      navigate(`/tools/${t.slug}`);
                    }}
                    className={`w-full text-left px-4 py-2 text-sm transition-colors flex items-center gap-2 ${
                      t.slug === slug
                        ? 'text-[#E2E85C] bg-white/5'
                        : 'text-white/60 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {t.title}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button onClick={() => navigate('/tools')} className="text-white/60 hover:text-white transition-colors">
            <X size={20} strokeWidth={1.5} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 flex gap-6 overflow-hidden">
          {/* Left Panel */}
          <div className="flex flex-col gap-5 w-[280px] h-full overflow-y-auto pr-1 custom-scrollbar">
            {/* Upload Zone */}
            {tool.requiresImage !== false && (
              <div className="flex flex-col gap-3 h-[200px] flex-shrink-0">
                <span className="text-white/60 text-xs">{tool.uploadLabel}</span>
                <UploadZone
                  label={`点击或拖拽上传`}
                  hint={tool.uploadHint}
                  onFileSelect={handleFileSelect}
                  onClear={() => { setImageFile(null); setImageBase64(null); }}
                />
              </div>
            )}

            {/* Dual Image Upload */}
            {tool.hasDualImage && (
              <div className="flex flex-col gap-3 h-[200px] flex-shrink-0">
                <span className="text-white/60 text-xs">{tool.dualImageLabel || '上传参考图片'}</span>
                <UploadZone
                  label="点击或拖拽上传参考图"
                  hint={tool.uploadHint}
                  onFileSelect={handleSecondFileSelect}
                  onClear={() => { setSecondImageFile(null); setSecondImageBase64(null); }}
                />
              </div>
            )}

            {/* Prompt */}
            {tool.hasPrompt && (
              <div className="flex flex-col gap-3 flex-1 min-h-[100px]">
                <span className="text-white/60 text-xs">提示词</span>
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  className="w-full h-full min-h-[80px] bg-white/5 border border-white/10 p-4 text-white/80 text-sm resize-none focus:outline-none focus:border-white/30 transition-colors placeholder:text-white/20"
                  placeholder={tool.promptPlaceholder || '输入提示词...'}
                />
              </div>
            )}

            {/* Room Selector */}
            {tool.hasRoomSelect && (
              <RoomSelector value={roomType} onChange={setRoomType} />
            )}

            {/* Custom Params */}
            <ParamPanel
              params={tool.customParams}
              values={paramValues}
              onChange={(key, val) => setParamValues((prev) => ({ ...prev, [key]: val }))}
            />

            {/* Project Selector */}
            <div className="flex flex-col gap-2 flex-shrink-0">
              <span className="text-white/60 text-xs">所属项目</span>
              <div className="flex gap-2">
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="flex-1 h-9 bg-white/5 border border-white/10 px-3 text-white/80 text-sm focus:outline-none focus:border-white/30"
                >
                  {projects.length === 0 && (
                    <option value="" className="bg-[#1a1a1a] text-white">
                      自动归档到默认项目
                    </option>
                  )}
                  {projects.map((p) => (
                    <option key={p.id} value={p.id} className="bg-[#1a1a1a] text-white">
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => navigate('/projects')}
                  className="h-9 px-3 bg-white/10 hover:bg-white/20 text-white/70 text-xs"
                >
                  管理
                </button>
              </div>
              {projectLoadError && (
                <span className="text-[11px] text-white/35">{projectLoadError}</span>
              )}
            </div>

            {/* Resolution */}
            {tool.hasResolution && (
              <div className="flex flex-col gap-3 flex-shrink-0">
                <span className="text-white/60 text-xs">分辨率</span>
                <div className="grid grid-cols-5 gap-2">
                  {availableResolutions.map((res) => (
                    <button
                      key={res.value}
                      onClick={() => resolutionEnabled && setSelectedResolution(res.value)}
                      disabled={!resolutionEnabled}
                      className={`h-8 text-xs transition-colors border ${
                        selectedResolution === res.value
                          ? 'bg-[#E2E85C] text-black border-[#E2E85C]'
                          : 'bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white'
                      } ${!resolutionEnabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                    >
                      {res.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Aspect Ratio */}
            {tool.hasAspectRatio && (
              <div className="flex flex-col gap-3 flex-shrink-0">
                <span className="text-white/60 text-xs">生成比例</span>
                <div className="grid grid-cols-6 gap-2">
                  {aspectRatios.map((ratio) => (
                    <button
                      key={ratio.value}
                      onClick={() => aspectRatioEnabled && setSelectedRatio(ratio.value)}
                      disabled={!aspectRatioEnabled}
                      className={`h-8 text-xs transition-colors border ${
                        selectedRatio === ratio.value
                          ? 'bg-[#E2E85C] text-black border-[#E2E85C]'
                          : 'bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white'
                      } ${!aspectRatioEnabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                    >
                      {ratio.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* P0 开关：布局强约束、跳过翻译（仅图生图工具显示），默认折叠 */}
            {showP0Switches && (
              <div className="flex flex-col flex-shrink-0 border border-white/10">
                <button
                  type="button"
                  onClick={() => setAdvancedOpen((v) => !v)}
                  className="flex items-center justify-between px-3 py-2 text-white/60 text-xs hover:text-white/80 transition-colors"
                >
                  高级选项
                  <ChevronDown
                    size={14}
                    className={`transition-transform duration-200 ${advancedOpen ? 'rotate-180' : ''}`}
                  />
                </button>
                {advancedOpen && (
                  <div className="flex flex-col gap-2 px-3 pb-3">
                    <label className="flex items-center gap-2 text-white/80 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={layoutStrict}
                        onChange={(e) => setLayoutStrict(e.target.checked)}
                        className="w-4 h-4 accent-[#E2E85C] bg-white/5 border-white/20"
                      />
                      布局强约束（严格保持布局、视角，不增删物体）
                    </label>
                    <label className="flex items-center gap-2 text-white/80 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={skipTranslation}
                        onChange={(e) => setSkipTranslation(e.target.checked)}
                        className="w-4 h-4 accent-[#E2E85C] bg-white/5 border-white/20"
                      />
                      跳过翻译（直接使用输入的提示词，中文可能影响效果）
                    </label>
                  </div>
                )}
              </div>
            )}

            {/* Region Canvas */}
            {tool.hasRegion && (
              <div className="flex flex-col gap-2 flex-shrink-0">
                <span className="text-white/60 text-xs">区域选择</span>
                <RegionCanvas
                  imageBase64={imageBase64}
                  value={regionData}
                  onChange={setRegionData}
                  placeholder="请先上传图片"
                  height={160}
                />
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={
                isGenerating ||
                (tool.requiresImage !== false && !imageBase64) ||
                (tool.hasDualImage &&
                  (!imageBase64 || (tool.requiresSecondImage !== false && !secondImageBase64))) ||
                (requiresRegionForGenerate && !regionData) ||
                (tool.hasPrompt && tool.requiresImage === false && !promptText.trim())
              }
              className="w-full h-10 bg-[#E2E85C] hover:bg-[#E2E85C] text-black text-sm font-medium transition-all opacity-60 hover:opacity-100 disabled:opacity-30 flex items-center justify-center gap-2 group flex-shrink-0"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  立即生成
                  <div className="flex items-center gap-1 text-black/60 text-xs group-hover:text-black/80">
                    <Zap size={12} fill="currentColor" />
                    <span>-{displayCost} 算力</span>
                  </div>
                </>
              )}
            </button>
          </div>

          {/* Right Panel — Result */}
          <div className="flex-1 bg-white/5 border-l border-white/10 flex flex-col items-center justify-center -my-6 -mr-6 ml-0 relative group">
            {error && (
              <div className="absolute top-6 left-6 right-6 bg-red-500/20 border border-red-500/30 px-4 py-2 text-red-300 text-sm">
                {error}
              </div>
            )}

            {isGenerating && (
              <div className="flex flex-col items-center gap-4">
                <Loader2 size={32} className="animate-spin text-[#E2E85C]/60" />
                <span className="text-white/40 text-sm">AI 正在生成...</span>
              </div>
            )}

            {!isGenerating && resultImage && (
              <img
                src={resultImage}
                alt="Generated"
                className="max-w-full max-h-full object-contain cursor-zoom-in"
                onClick={() => setShowPreview(true)}
              />
            )}

            {!isGenerating && resultText && !resultImage && (
              <div className="w-full h-full px-8 py-6 text-white/60 font-mono text-xs overflow-auto">
                {(() => {
                  try {
                    const parsed = JSON.parse(resultText);
                    return (
                      <pre className="text-left whitespace-pre-wrap break-words">
                        {JSON.stringify(parsed, null, 2)}
                      </pre>
                    );
                  } catch {
                    return (
                      <pre className="text-left whitespace-pre-wrap break-words">
                        {resultText}
                      </pre>
                    );
                  }
                })()}
              </div>
            )}

            {!isGenerating && !resultImage && !resultText && !error && (
              <span className="text-white/20">生成结果区域</span>
            )}

            {/* Download */}
            {resultImage && (
              <button
                className="absolute top-6 right-6 p-2 bg-black/50 hover:bg-[#E2E85C] text-white hover:text-black transition-colors opacity-0 group-hover:opacity-100"
                title="下载图片"
                onClick={async () => {
                  try {
                    const res = await fetch(resultImage);
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${tool.slug}-result.jpg`;
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch {
                    window.open(resultImage, '_blank');
                  }
                }}
              >
                <Download size={20} strokeWidth={1.5} />
              </button>
            )}
          </div>
        </div>
      </div>

      <BackButton />
      <SideNavBar />
      <UserProfile />

      {/* Watermark */}
      <div className="fixed top-[60px] left-[120px] w-[220px] h-[20px] flex items-center justify-center z-0 pointer-events-none">
        <span className="text-white font-handwriting drop-shadow-lg" style={{ fontFamily: "'Pinyon Script', cursive", fontSize: '4rem', marginBottom: '13px', opacity: 0.1 }}>
          design
        </span>
      </div>

      {/* Logo */}
      <div className="fixed top-[80px] left-[120px] w-[220px] h-[20px] flex items-center justify-start z-50">
        <img src={logoWhite} alt="Logo" className="h-full w-auto object-contain opacity-90" />
      </div>

      {/* Fullscreen Preview */}
      {showPreview && resultImage && (
        <div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center cursor-zoom-out"
          onClick={() => setShowPreview(false)}
        >
          <img
            src={resultImage}
            alt="Preview"
            className="max-w-[95vw] max-h-[95vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            onClick={() => setShowPreview(false)}
            className="absolute top-6 right-6 p-2 bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X size={24} strokeWidth={1.5} />
          </button>
          <button
            className="absolute bottom-6 right-6 p-2 bg-white/10 hover:bg-[#E2E85C] text-white hover:text-black transition-colors"
            title="下载图片"
            onClick={async (e) => {
              e.stopPropagation();
              try {
                const res = await fetch(resultImage);
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${tool.slug}-result.jpg`;
                a.click();
                URL.revokeObjectURL(url);
              } catch {
                window.open(resultImage, '_blank');
              }
            }}
          >
            <Download size={20} strokeWidth={1.5} />
          </button>
        </div>
      )}
    </div>
  );
};

export default ToolDetail;
