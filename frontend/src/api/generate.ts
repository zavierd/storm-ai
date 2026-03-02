import type { ToolConfig } from '../config/toolConfigs';
import type { RegionData } from '../components/ToolDetail/RegionCanvas';
import { getAuthHeader } from '../stores/useAuthStore';

export interface GenerateParams {
  featureKey: string;
  projectId?: string;
  imageBase64?: string;
  secondImageBase64?: string;
  promptText?: string;
  resolution?: string;
  aspectRatio?: string;
  /** 区域选择数据，用于 partial-replace、material-replace、local-lighting、add-model 等 */
  region?: RegionData | null;
  extraParams?: Record<string, string | number | boolean>;
  /** P0-1: 布局保持强化，启用强约束（严格保持布局、视角、空间比例，不增删物体） */
  layoutStrict?: boolean;
  /** P0-2: 跳过翻译，直接使用用户输入的提示词（中文可能影响效果） */
  skipTranslation?: boolean;
}

export interface GenerateResult {
  success: boolean;
  imageUrl?: string;
  imageBase64?: string;
  text?: string;
  error?: string;
  errorCode?: string;
  usage?: Record<string, unknown>;
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

const CATEGORY_PATH: Record<string, string> = {
  interior_ai: 'interior-ai',
  super_ai: 'super-ai',
  toolbox: 'toolbox',
  human: 'toolbox',
};

export async function generateImage(
  tool: ToolConfig,
  params: GenerateParams
): Promise<GenerateResult> {
  const path = CATEGORY_PATH[tool.category] || 'toolbox';
  const url = `${API_BASE}/${path}/${params.featureKey}`;

  const normalizedExtraParams: Record<string, string | number | boolean> = {
    ...(params.extraParams || {}),
  };

  const body: Record<string, unknown> = {
    images: [],
    project_id: params.projectId || null,
    prompt_text: params.promptText || null,
    extra_params: normalizedExtraParams,
  };
  if (params.layoutStrict !== undefined) body.layout_strict = params.layoutStrict;
  if (params.skipTranslation !== undefined) body.skip_translation = params.skipTranslation;
  if (params.aspectRatio && params.aspectRatio !== 'default') {
    body.aspect_ratio = params.aspectRatio;
  }
  if (params.region && (params.region.type === 'rect' || params.region.type === 'mask')) {
    body.region = params.region;
  }

  if (params.imageBase64) {
    (body.images as unknown[]).push({
      base64_data: params.imageBase64,
      format: 'png',
    });
  }
  if (params.secondImageBase64) {
    (body.images as unknown[]).push({
      base64_data: params.secondImageBase64,
      format: 'png',
    });
  }

  const RESOLUTION_MAP: Record<string, string> = {
    '720p': '720P',
    '1080p': '1K',
    '2k': '2K',
    '4k': '4K',
  };
  if (params.resolution) {
    const preset =
      RESOLUTION_MAP[params.resolution.toLowerCase()] ??
      params.resolution.toUpperCase();
    body.resolution = { preset };
  }

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const errorMsg = errData.error?.message || errData.detail || errData.message || `服务器错误: ${res.status}`;
      return { success: false, error: errorMsg, errorCode: errData.error?.code };
    }

    const data = await res.json();

    if (!data.success) {
      return {
        success: false,
        error: data.error?.message || data.error || '生成失败',
        errorCode: data.error?.code,
      };
    }

    return {
      success: true,
      imageUrl: data.image_urls?.[0] || undefined,
      imageBase64: data.images?.[0] ? `data:image/png;base64,${data.images[0]}` : undefined,
      text: data.texts?.[0] || undefined,
      usage: data.usage || undefined,
    };
  } catch {
    return { success: false, error: '网络连接失败，请检查后端服务是否启动' };
  }
}
