import axios from 'axios'
import { message } from 'antd'

export type PlainObject = Record<string, unknown>

export interface PaginatedResult<T> {
  items: T[]
  total: number
}

const http = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

const isPlainObject = (value: unknown): value is PlainObject =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const toNumber = (value: unknown, fallback: number) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return fallback
}

export const normalizeListResponse = <T,>(payload: unknown): PaginatedResult<T> => {
  if (Array.isArray(payload)) {
    return { items: payload as T[], total: payload.length }
  }

  if (!isPlainObject(payload)) {
    return { items: [], total: 0 }
  }

  const listKeys = ['items', 'list', 'records', 'rows', 'data']
  const totalKeys = ['total', 'count', 'total_count', 'totalCount']

  let items: T[] = []
  for (const key of listKeys) {
    const value = payload[key]
    if (Array.isArray(value)) {
      items = value as T[]
      break
    }
  }

  const total =
    totalKeys.reduce<number | null>((result, key) => {
      if (result !== null) {
        return result
      }
      if (key in payload) {
        return toNumber(payload[key], items.length)
      }
      return null
    }, null) ?? items.length

  return { items, total }
}

export const normalizeDetailResponse = <T,>(payload: unknown): T =>
  (isPlainObject(payload) ? payload : {}) as T

http.interceptors.response.use(
  (response) => {
    const payload = response.data as PlainObject
    const code = typeof payload.code === 'number' ? payload.code : 0
    const msg = typeof payload.message === 'string' ? payload.message : ''
    const data = payload.data

    if (code !== 0) {
      message.error(msg || '请求失败')
      return Promise.reject(new Error(msg || '请求失败'))
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return data as any
  },
  (error) => {
    const responseData = isPlainObject(error.response?.data) ? error.response.data : {}
    const msg =
      (typeof responseData.message === 'string' && responseData.message) ||
      error.message ||
      '网络错误'
    message.error(msg)
    return Promise.reject(error)
  },
)

export default http

export const modelApi = {
  list: (params?: object) => http.get('/models', { params }),
  create: (data: object) => http.post('/models', data),
  get: (id: number) => http.get(`/models/${id}`),
  update: (id: number, data: object) => http.put(`/models/${id}`, data),
  delete: (id: number) => http.delete(`/models/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/models/${id}/toggle`, { enabled }),
}

export const toolApi = {
  list: (params?: object) => http.get('/tools', { params }),
  create: (data: object) => http.post('/tools', data),
  get: (id: number) => http.get(`/tools/${id}`),
  update: (id: number, data: object) => http.put(`/tools/${id}`, data),
  delete: (id: number) => http.delete(`/tools/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/tools/${id}/toggle`, { enabled }),
}

export const skillApi = {
  list: (params?: object) => http.get('/skills', { params }),
  create: (data: object) => http.post('/skills', data),
  get: (id: number) => http.get(`/skills/${id}`),
  update: (id: number, data: object) => http.put(`/skills/${id}`, data),
  delete: (id: number) => http.delete(`/skills/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/skills/${id}/toggle`, { enabled }),
}

export const agentApi = {
  list: (params?: object) => http.get('/agents', { params }),
  create: (data: object) => http.post('/agents', data),
  get: (id: number) => http.get(`/agents/${id}`),
  update: (id: number, data: object) => http.put(`/agents/${id}`, data),
  delete: (id: number) => http.delete(`/agents/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/agents/${id}/toggle`, { enabled }),
  ping: (id: number) => http.post(`/agents/${id}/ping`),
  publish: (id: number, status: string, subAgentIds: number[] = []) =>
    http.patch(`/agents/${id}/publish`, { status, sub_agent_ids: subAgentIds }),
}

export const pipelineApi = {
  list: (params?: object) => http.get('/pipelines', { params }),
  create: (data: object) => http.post('/pipelines', data),
  get: (id: number) => http.get(`/pipelines/${id}`),
  update: (id: number, data: object) => http.put(`/pipelines/${id}`, data),
  delete: (id: number) => http.delete(`/pipelines/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/pipelines/${id}/toggle`, { enabled }),
}

export const detectionRuleApi = {
  list: (params?: object) => http.get('/detection-rules', { params }),
  create: (data: object) => http.post('/detection-rules', data),
  get: (id: number) => http.get(`/detection-rules/${id}`),
  update: (id: number, data: object) => http.put(`/detection-rules/${id}`, data),
  delete: (id: number) => http.delete(`/detection-rules/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/detection-rules/${id}/toggle`, { enabled }),
}

export const mcpServerApi = {
  list: (params?: object) => http.get('/mcp-servers', { params }),
  create: (data: object) => http.post('/mcp-servers', data),
  get: (id: number) => http.get(`/mcp-servers/${id}`),
  update: (id: number, data: object) => http.put(`/mcp-servers/${id}`, data),
  delete: (id: number) => http.delete(`/mcp-servers/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/mcp-servers/${id}/toggle`, { enabled }),
  connect: (id: number) => http.post(`/mcp-servers/${id}/connect`),
  discover: (id: number) => http.post(`/mcp-servers/${id}/discover`),
}

export const workflowApi = {
  list: (params?: object) => http.get('/workflows', { params }),
  create: (data: object) => http.post('/workflows', data),
  get: (id: number) => http.get(`/workflows/${id}`),
  update: (id: number, data: object) => http.put(`/workflows/${id}`, data),
  delete: (id: number) => http.delete(`/workflows/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/workflows/${id}/toggle`, { enabled }),
}
