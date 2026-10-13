import type {
  ApprovalRequest, Cash, EventsResponse, RunInfo, TicketDetail, TicketList,
} from './types'

// The FastAPI backend from Problem 7.
export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = body?.detail
    const msg = typeof detail === 'string' ? detail : detail?.error ?? JSON.stringify(detail ?? body)
    throw new Error(msg)
  }
  return body as T
}

export const api = {
  tickets: () => call<TicketList>('/api/tickets'),
  ticket: (id: number) => call<TicketDetail>(`/api/tickets/${id}`),
  runTicket: (id: number) => call<RunInfo>(`/api/tickets/${id}/run`, { method: 'POST' }),
  run: (runId: string) => call<RunInfo>(`/api/runs/${runId}`),
  events: (after = -1, limit = 1000) =>
    call<EventsResponse>(`/api/events?after=${after}&limit=${limit}`),
  approvals: (status = 'pending') =>
    call<{ status: string; requests: ApprovalRequest[] }>(`/api/approvals?status=${status}`),
  approve: (id: number, approvedBy: string) =>
    call<Record<string, unknown>>(`/api/approvals/${id}/approve`, {
      method: 'POST', body: JSON.stringify({ approved_by: approvedBy }),
    }),
  reject: (id: number, decidedBy: string, note: string) =>
    call<Record<string, unknown>>(`/api/approvals/${id}/reject`, {
      method: 'POST', body: JSON.stringify({ decided_by: decidedBy, note }),
    }),
  cash: () => call<Cash>('/api/cash'),
  reset: () => call<{ reset: boolean }>('/api/reset', { method: 'POST' }),
}
