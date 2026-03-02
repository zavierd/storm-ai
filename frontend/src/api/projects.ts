import { getAuthHeader } from '../stores/useAuthStore';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';

export interface ProjectRecord {
  id: string;
  name: string;
  cover_image_url?: string | null;
  is_default: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  image_count?: number;
  last_generated_at?: string | null;
}

export interface GenerationRecord {
  id: string;
  project_id: string;
  feature_key: string;
  prompt_text?: string | null;
  room_type?: string | null;
  result_image_url?: string | null;
  credits_cost?: number;
  created_at?: string | null;
}

async function parseError(res: Response): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return data.error || data.detail || data.message || `请求失败: ${res.status}`;
}

export async function listProjects(limit = 20, offset = 0): Promise<ProjectRecord[]> {
  const res = await fetch(`${API_BASE}/projects?limit=${limit}&offset=${offset}`, {
    headers: { ...getAuthHeader() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.records || [];
}

export async function createProject(name: string): Promise<ProjectRecord> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.record;
}

export async function updateProjectName(projectId: string, name: string): Promise<ProjectRecord> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.record;
}

export async function getProject(projectId: string): Promise<ProjectRecord> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`, {
    headers: { ...getAuthHeader() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return data.record;
}

export async function listProjectGenerations(
  projectId: string,
  limit = 20,
  offset = 0
): Promise<{ project: ProjectRecord; records: GenerationRecord[] }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/generations?limit=${limit}&offset=${offset}`, {
    headers: { ...getAuthHeader() },
  });
  if (!res.ok) throw new Error(await parseError(res));
  const data = await res.json();
  return { project: data.project, records: data.records || [] };
}

