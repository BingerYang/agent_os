import axios, { type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  timestamp: string
}

const http = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || '') + '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

http.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { code, message, data } = response.data
    if (code !== 0) {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
    return data as any
  },
  (error) => {
    const msg = error.response?.data?.message || error.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http

// 模型配置
export const modelApi = {
  list: (params?: object) => http.get('/models', { params }),
  create: (data: object) => http.post('/models', data),
  get: (id: number) => http.get(`/models/${id}`),
  update: (id: number, data: object) => http.put(`/models/${id}`, data),
  delete: (id: number) => http.delete(`/models/${id}`)
}

// 工具管理
export const toolApi = {
  list: (params?: object) => http.get('/tools', { params }),
  create: (data: object) => http.post('/tools', data),
  get: (id: number) => http.get(`/tools/${id}`),
  update: (id: number, data: object) => http.put(`/tools/${id}`, data),
  delete: (id: number) => http.delete(`/tools/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/tools/${id}/toggle`, { enabled })
}

// 技能管理
export const skillApi = {
  list: (params?: object) => http.get('/skills', { params }),
  create: (data: object) => http.post('/skills', data),
  get: (id: number) => http.get(`/skills/${id}`),
  update: (id: number, data: object) => http.put(`/skills/${id}`, data),
  delete: (id: number) => http.delete(`/skills/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/skills/${id}/toggle`, { enabled })
}

// Agent 管理
export const agentApi = {
  list: (params?: object) => http.get('/agents', { params }),
  create: (data: object) => http.post('/agents', data),
  get: (id: number) => http.get(`/agents/${id}`),
  update: (id: number, data: object) => http.put(`/agents/${id}`, data),
  delete: (id: number) => http.delete(`/agents/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/agents/${id}/toggle`, { enabled }),
  ping: (id: number) => http.post(`/agents/${id}/ping`)
}

// 流水线管理
export const pipelineApi = {
  list: (params?: object) => http.get('/pipelines', { params }),
  create: (data: object) => http.post('/pipelines', data),
  get: (id: number) => http.get(`/pipelines/${id}`),
  update: (id: number, data: object) => http.put(`/pipelines/${id}`, data),
  delete: (id: number) => http.delete(`/pipelines/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/pipelines/${id}/toggle`, { enabled })
}

// 检测规则
export const detectionRuleApi = {
  list: (params?: object) => http.get('/detection-rules', { params }),
  create: (data: object) => http.post('/detection-rules', data),
  get: (id: number) => http.get(`/detection-rules/${id}`),
  update: (id: number, data: object) => http.put(`/detection-rules/${id}`, data),
  delete: (id: number) => http.delete(`/detection-rules/${id}`),
  toggle: (id: number, enabled: boolean) => http.patch(`/detection-rules/${id}/toggle`, { enabled })
}

// 商场
export const marketplaceApi = {
  list: (params?: object) => http.get('/marketplace', { params }),
  install: (type: string, id: number) => http.post(`/marketplace/${type}/${id}/install`),
  uninstall: (type: string, id: number) => http.delete(`/marketplace/${type}/${id}/install`),
  registerAgent: (data: object) => http.post('/marketplace/agents', data)
}

// 查询
export const queryApi = {
  submit: (data: object) => http.post('/query', data)
}
