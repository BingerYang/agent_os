import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { marketplaceApi, toolApi, skillApi, agentApi } from '@/api/index'

export type MarketplaceItemType = 'tool' | 'skill' | 'agent'

export interface MarketplaceItem {
  id: number
  name: string
  description: string
  item_type: MarketplaceItemType
  enabled: boolean
  tags: string[]
  version: string
  source_platform: string
}

export interface MarketplaceQueryParams {
  item_type?: MarketplaceItemType
  enabled?: boolean
  keyword?: string
}

export interface RegisterMarketplaceAgentData {
  name: string
  access_url: string
  access_token: string
  description: string
}

export interface MarketplaceTogglePayload {
  id: number
  item_type: MarketplaceItemType
  enabled: boolean
}

export interface CreateToolData {
  name: string
  display_name: string
  description?: string
  protocol: string
  endpoint_url?: string
  auth_type?: string
  auth_config?: Record<string, string> | null
  tags?: string[]
  version?: string
}

export interface CreateSkillData {
  name: string
  description?: string
  trigger_condition?: string
  tags?: string[]
  version?: string
}

interface MarketplaceListResponse {
  items?: MarketplaceItem[]
}

interface MarketplaceInstallResponse {
  id: number
  enabled: boolean
}

export const useMarketplaceStore = defineStore('marketplace', () => {
  const items = ref<MarketplaceItem[]>([])
  const loading = ref(false)
  const installing = ref<Record<string, boolean>>({})
  const lastQuery = ref<MarketplaceQueryParams>()

  function getInstallingKey(item_type: string, item_id: number) {
    return `${item_type}_${item_id}`
  }

  function updateLocalItem(item_type: string, item_id: number, patch: Partial<MarketplaceItem>) {
    const index = items.value.findIndex(item => item.item_type === item_type && item.id === item_id)
    if (index === -1) return
    items.value[index] = { ...items.value[index], ...patch }
  }

  async function fetchItems(params?: MarketplaceQueryParams) {
    loading.value = true
    lastQuery.value = params
    try {
      const data = await marketplaceApi.list(params) as MarketplaceListResponse
      items.value = data.items || []
      return data
    } finally {
      loading.value = false
    }
  }

  async function installItem(item_type: string, item_id: number) {
    const key = getInstallingKey(item_type, item_id)
    installing.value[key] = true
    try {
      const data = await marketplaceApi.install(item_type, item_id) as MarketplaceInstallResponse
      updateLocalItem(item_type, item_id, { enabled: data.enabled })
      if (lastQuery.value?.enabled !== undefined && lastQuery.value.enabled !== data.enabled) {
        items.value = items.value.filter(item => !(item.item_type === item_type && item.id === item_id))
      }
      ElMessage.success('安装成功')
      return data
    } finally {
      delete installing.value[key]
    }
  }

  async function uninstallItem(item_type: string, item_id: number) {
    const key = getInstallingKey(item_type, item_id)
    installing.value[key] = true
    try {
      const data = await marketplaceApi.uninstall(item_type, item_id) as MarketplaceInstallResponse
      updateLocalItem(item_type, item_id, { enabled: data.enabled })
      if (lastQuery.value?.enabled !== undefined && lastQuery.value.enabled !== data.enabled) {
        items.value = items.value.filter(item => !(item.item_type === item_type && item.id === item_id))
      }
      ElMessage.success('卸载成功')
      return data
    } finally {
      delete installing.value[key]
    }
  }

  async function registerAgent(data: RegisterMarketplaceAgentData) {
    const result = await marketplaceApi.registerAgent(data)
    ElMessage.success('注册成功')
    return result
  }

  async function createTool(data: CreateToolData) {
    const result = await toolApi.create(data)
    ElMessage.success('工具添加成功')
    return result
  }

  async function createSkill(data: CreateSkillData) {
    const result = await skillApi.create(data)
    ElMessage.success('技能添加成功')
    return result
  }

  async function deleteItem(item_type: MarketplaceItemType, item_id: number) {
    if (item_type === 'tool') {
      await toolApi.delete(item_id)
    } else if (item_type === 'skill') {
      await skillApi.delete(item_id)
    } else {
      await agentApi.delete(item_id)
    }
    items.value = items.value.filter(
      (i) => !(i.item_type === item_type && i.id === item_id)
    )
    ElMessage.success('已删除')
  }

  return {
    items,
    loading,
    installing,
    fetchItems,
    installItem,
    uninstallItem,
    registerAgent,
    createTool,
    createSkill,
    deleteItem,
  }
})
