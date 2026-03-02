import { getAuthHeader } from '../stores/useAuthStore';
import type { GenerationRecord } from './projects';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

async function parseError(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return data.error || data.detail || data.message || `请求失败: ${res.status}`;
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export type CreditHistoryRecord = GenerationRecord & {
  amount?: number;
  reason?: string | null;
};

function normalizeHistoryRecord(raw: any): CreditHistoryRecord {
  const amountFromApi = toFiniteNumber(raw?.amount, Number.NaN);
  const legacyCost = toFiniteNumber(raw?.credits_cost, Number.NaN);
  // 优先使用 amount 语义（保留正负方向）；仅旧接口无 amount 时回退到 credits_cost。
  const amount = Number.isFinite(amountFromApi)
    ? amountFromApi
    : Number.isFinite(legacyCost)
      ? -Math.abs(legacyCost)
      : 0;
  const creditsCost = amount < 0 ? Math.abs(amount) : 0;

  return {
    id: String(raw?.id ?? ''),
    // 新账变记录无 project_id，保留旧字段并回填空字符串避免运行时报错
    project_id: String(raw?.project_id ?? ''),
    feature_key: String(raw?.feature_key ?? ''),
    // 新口径中的 reason 映射到旧视图常用的 prompt_text 兜底字段
    prompt_text: raw?.prompt_text ?? raw?.reason ?? null,
    room_type: raw?.room_type ?? null,
    result_image_url: raw?.result_image_url ?? null,
    credits_cost: creditsCost,
    amount,
    reason: raw?.reason ?? null,
    created_at: raw?.created_at ?? null,
  };
}

export async function listGenerationHistory(limit = 20, offset = 0): Promise<CreditHistoryRecord[]> {
  const res = await fetch(`${API_BASE}/credits/history?limit=${limit}&offset=${offset}`, {
    headers: { ...getAuthHeader() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  const records = Array.isArray(data?.records) ? data.records : [];
  return records.map(normalizeHistoryRecord).filter((record) => !!record.id);
}

