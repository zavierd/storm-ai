import { getAuthHeader } from '../stores/useAuthStore';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

function buildUrl(endpoint: string): string {
  const base = API_BASE.replace(/\/+$/, '');
  const normalizedEndpoint =
    /^\/api\//.test(endpoint) && /\/api(?:\/v\d+)?$/i.test(base)
      ? endpoint.replace(/^\/api/, '')
      : endpoint;
  return `${base}${normalizedEndpoint}`;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface CreateDowngradeRequest {
  targetPriceId: string;
  subscriptionId: string;
}

export interface UpdateDowngradeRequest {
  targetPriceId?: string;
  subscriptionId?: string;
  effectiveAt?: string;
}

export interface CancelDowngradeRequest {
  subscriptionId?: string;
  downgradeId?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(url: string, options?: RequestInit): Promise<ApiResult<T>> {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
      ...options,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const errorMsg =
        errData.error?.message || errData.detail || errData.message || `服务器错误: ${res.status}`;
      return { success: false, error: errorMsg };
    }

    const data = (await res.json()) as T;
    return { success: true, data };
  } catch {
    return { success: false, error: '网络连接失败，请检查后端服务是否启动' };
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getDowngradeOptions(): Promise<ApiResult> {
  return request(buildUrl('/api/get-downgrade-options'));
}

export async function createDowngrade(payload: CreateDowngradeRequest): Promise<ApiResult> {
  return request(buildUrl('/api/create-downgrade'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getPendingDowngrade(): Promise<ApiResult> {
  return request(buildUrl('/api/get-pending-downgrade'));
}

export async function updateDowngrade(payload: UpdateDowngradeRequest): Promise<ApiResult> {
  return request(buildUrl('/api/update-downgrade'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function cancelDowngrade(payload: CancelDowngradeRequest): Promise<ApiResult> {
  return request(buildUrl('/api/cancel-downgrade'), {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
