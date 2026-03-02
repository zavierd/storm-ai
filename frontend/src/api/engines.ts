import { getAuthHeader } from '../stores/useAuthStore';
import type { EngineTypeKey } from '../config/toolConfigs';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

interface EngineItem {
  key: string;
  type: EngineTypeKey;
  label: string;
  is_default: boolean;
}

interface EngineListResponse {
  engines: EngineItem[];
  default: string | null;
}

export async function getDefaultEngineType(): Promise<EngineTypeKey | null> {
  const res = await fetch(`${API_BASE}/engines/list`, {
    headers: { ...getAuthHeader() },
  });
  if (!res.ok) return null;

  const data = (await res.json()) as EngineListResponse;
  const engines = data.engines || [];
  if (engines.length === 0) return null;

  if (data.default) {
    const byKey = engines.find((e) => e.key === data.default);
    if (byKey?.type) return byKey.type;
  }

  const byFlag = engines.find((e) => e.is_default);
  return byFlag?.type || engines[0].type || null;
}
