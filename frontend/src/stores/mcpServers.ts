import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { mcpServerApi } from '@/api/index'

export interface MCPServer {
  id: number
  name: string
  display_name: string
  description: string | null
  transport_type: 'STDIO' | 'HTTP_SSE'
  command: string | null
  args: string[] | null
  env_vars: Record<string, string> | null
  endpoint_url: string | null
  auth_type: 'NONE' | 'API_KEY' | 'BEARER_TOKEN' | 'BASIC_AUTH'
  auth_config: Record<string, string> | null
  status: 'UNKNOWN' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'
  last_connected_at: string | null
  enabled: boolean
  created_at: string
  updated_at: string
}

export const useMCPServersStore = defineStore('mcpServers', () => {
  const servers = ref<MCPServer[]>([])
  const loading = ref(false)
  const total = ref(0)

  async function fetchServers(params?: object) {
    loading.value = true
    try {
      const data = await mcpServerApi.list(params) as { items?: MCPServer[]; total?: number }
      servers.value = data.items || []
      total.value = data.total || 0
    } finally {
      loading.value = false
    }
  }

  async function createServer(data: object) {
    const result = await mcpServerApi.create(data)
    ElMessage.success('创建成功')
    return result
  }

  async function updateServer(id: number, data: object) {
    const result = await mcpServerApi.update(id, data)
    ElMessage.success('更新成功')
    return result
  }

  async function deleteServer(id: number) {
    await mcpServerApi.delete(id)
    ElMessage.success('删除成功')
    servers.value = servers.value.filter(s => s.id !== id)
  }

  async function toggleServer(id: number, enabled: boolean) {
    const result = await mcpServerApi.toggle(id, enabled) as MCPServer
    const idx = servers.value.findIndex(s => s.id === id)
    if (idx !== -1) servers.value[idx] = { ...servers.value[idx], enabled }
    ElMessage.success(enabled ? '已启用' : '已禁用')
    return result
  }

  async function connectServer(id: number) {
    const result = await mcpServerApi.connect(id) as { status: string; latency_ms?: number; error?: string }
    const idx = servers.value.findIndex(s => s.id === id)
    if (idx !== -1) servers.value[idx] = { ...servers.value[idx], status: result.status as MCPServer['status'] }
    return result
  }

  async function discoverTools(id: number) {
    const result = await mcpServerApi.discover(id) as { new_tools: number; message: string }
    return result
  }

  return { servers, loading, total, fetchServers, createServer, updateServer, deleteServer, toggleServer, connectServer, discoverTools }
})
