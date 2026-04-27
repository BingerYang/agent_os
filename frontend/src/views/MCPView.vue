<template>
  <div class="page-container">
    <div class="page-header">
      <h2>工具库</h2>
      <p class="desc">管理工具（Tool），支持按来源 MCP Server 筛选</p>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索名称..." clearable style="width: 220px" @keyup.enter="fetchData" @clear="fetchData" />
      <el-select v-model="filterEnabled" placeholder="全部状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="已安装" :value="true" />
        <el-option label="未安装" :value="false" />
      </el-select>
      <el-select v-model="filterMcpServer" placeholder="来源 Server" clearable style="width: 160px" @change="fetchData">
        <el-option v-for="s in mcpServerOptions" :key="s.id" :label="s.display_name || s.name" :value="s.id" />
      </el-select>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
      <el-button type="primary" @click="addToolVisible = true">+ 添加工具</el-button>
    </div>

    <div v-loading="loading" class="card-grid">
      <MarketplaceCard
        v-for="item in filteredItems"
        :key="`${item.item_type}-${item.id}`"
        :item="item"
        :loading="Boolean(installing[`${item.item_type}_${item.id}`])"
        @toggle="handleToggle"
        @delete="handleDelete"
      />
      <el-empty v-if="!loading && filteredItems.length === 0" description="暂无条目" style="grid-column: 1 / -1" />
    </div>

    <el-dialog v-model="addToolVisible" title="添加工具 (Tool)" width="560px" destroy-on-close>
      <el-form :model="toolForm" :rules="toolRules" ref="toolFormRef" label-width="100px">
        <el-form-item label="名称" prop="name"><el-input v-model="toolForm.name" placeholder="唯一标识，如 web_search" /></el-form-item>
        <el-form-item label="显示名称" prop="display_name"><el-input v-model="toolForm.display_name" placeholder="用于展示的友好名称" /></el-form-item>
        <el-form-item label="协议" prop="protocol">
          <el-select v-model="toolForm.protocol" style="width:100%">
            <el-option label="MCP" value="MCP" />
            <el-option label="HTTP" value="HTTP" />
            <el-option label="内置 (BUILTIN)" value="BUILTIN" />
          </el-select>
        </el-form-item>
        <el-form-item label="端点地址"><el-input v-model="toolForm.endpoint_url" placeholder="仅 MCP/HTTP 需填写" /></el-form-item>
        <el-form-item label="认证方式">
          <el-select v-model="toolForm.authType" style="width:100%">
            <el-option label="无认证" value="NONE" />
            <el-option label="API Key" value="API_KEY" />
            <el-option label="Bearer Token" value="BEARER_TOKEN" />
            <el-option label="Basic Auth" value="BASIC_AUTH" />
          </el-select>
        </el-form-item>
        <template v-if="toolForm.authType === 'API_KEY'">
          <el-form-item label="Key 名称"><el-input v-model="toolForm.authKeyName" placeholder="如 X-API-Key" /></el-form-item>
          <el-form-item label="Key 值"><el-input v-model="toolForm.authKeyValue" placeholder="API Key 值" show-password /></el-form-item>
          <el-form-item label="传递位置">
            <el-radio-group v-model="toolForm.authKeyLocation">
              <el-radio value="header">Header</el-radio>
              <el-radio value="query">Query</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
        <el-form-item v-if="toolForm.authType === 'BEARER_TOKEN'" label="Token">
          <el-input v-model="toolForm.authToken" placeholder="Bearer Token 值" show-password />
        </el-form-item>
        <template v-if="toolForm.authType === 'BASIC_AUTH'">
          <el-form-item label="用户名"><el-input v-model="toolForm.authUsername" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="toolForm.authPassword" type="password" show-password /></el-form-item>
        </template>
        <el-form-item label="描述"><el-input v-model="toolForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="toolForm.tagsRaw" placeholder="逗号分隔，如: search,web" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addToolVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddTool">添加</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import MarketplaceCard from '@/components/marketplace/MarketplaceCard.vue'
import type { MarketplaceItemType, MarketplaceTogglePayload } from '@/stores/marketplace'
import { useMarketplaceStore } from '@/stores/marketplace'
import { mcpServerApi } from '@/api/index'
import { storeToRefs } from 'pinia'

const store = useMarketplaceStore()
const { items, loading, installing } = storeToRefs(store)

const keyword = ref('')
const filterEnabled = ref<boolean | null>(null)
const filterMcpServer = ref<number | null>(null)
const mcpServerOptions = ref<Array<{id: number; name: string; display_name: string}>>([])
const submitting = ref(false)

const filteredItems = computed(() => {
  const toolItems = items.value.filter((item) => item.item_type === 'tool')
  if (filterMcpServer.value == null) return toolItems

  const selectedServer = mcpServerOptions.value.find((server) => server.id === filterMcpServer.value)
  if (!selectedServer) return toolItems

  return toolItems.filter((item) => {
    const source = item.source_platform?.trim().toLowerCase()
    return source === selectedServer.name.trim().toLowerCase()
      || source === selectedServer.display_name.trim().toLowerCase()
  })
})

async function fetchMcpServers() {
  const data = await mcpServerApi.list({ page_size: 100, enabled: true }) as { items?: Array<{id: number; name: string; display_name: string}> }
  mcpServerOptions.value = data.items || []
}

const addToolVisible = ref(false)
const toolFormRef = ref()
const toolForm = reactive({
  name: '',
  display_name: '',
  protocol: 'HTTP',
  endpoint_url: '',
  description: '',
  tagsRaw: '',
  authType: 'NONE',
  authKeyName: '',
  authKeyValue: '',
  authKeyLocation: 'header',
  authToken: '',
  authUsername: '',
  authPassword: '',
})
const toolRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  protocol: [{ required: true, message: '请选择协议', trigger: 'change' }],
}

async function fetchData() {
  await store.fetchItems({
    item_type: 'tool',
    enabled: filterEnabled.value ?? undefined,
    keyword: keyword.value || undefined,
  })
}

async function handleToggle(payload: MarketplaceTogglePayload) {
  if (!payload.enabled) {
    try {
      await ElMessageBox.confirm('确认卸载此条目？', '卸载确认', { type: 'warning', confirmButtonText: '卸载', cancelButtonText: '取消' })
    } catch {
      await fetchData()
      return
    }
    await store.uninstallItem(payload.item_type, payload.id)
    return
  }
  await store.installItem(payload.item_type, payload.id)
}

async function handleDelete(payload: { id: number; item_type: MarketplaceItemType }) {
  try {
    await ElMessageBox.confirm('此操作将永久删除该条目，无法恢复。确认删除？', '删除确认', { type: 'error', confirmButtonText: '确认删除', cancelButtonText: '取消' })
  } catch { return }
  await store.deleteItem(payload.item_type, payload.id)
}

async function handleAddTool() {
  await toolFormRef.value.validate()
  submitting.value = true
  try {
    const tags = toolForm.tagsRaw ? toolForm.tagsRaw.split(',').map((t) => t.trim()).filter(Boolean) : []
    let auth_config: Record<string, string> | null = null
    if (toolForm.authType === 'API_KEY') {
      auth_config = { key_name: toolForm.authKeyName, key_value: toolForm.authKeyValue, key_location: toolForm.authKeyLocation }
    } else if (toolForm.authType === 'BEARER_TOKEN') {
      auth_config = { token: toolForm.authToken }
    } else if (toolForm.authType === 'BASIC_AUTH') {
      auth_config = { username: toolForm.authUsername, password: toolForm.authPassword }
    }
    await store.createTool({
      name: toolForm.name,
      display_name: toolForm.display_name,
      protocol: toolForm.protocol,
      endpoint_url: toolForm.endpoint_url || undefined,
      description: toolForm.description || undefined,
      tags,
      auth_type: toolForm.authType || undefined,
      auth_config,
    })
    await fetchData()
    addToolVisible.value = false
    Object.assign(toolForm, {
      name: '',
      display_name: '',
      protocol: 'HTTP',
      endpoint_url: '',
      description: '',
      tagsRaw: '',
      authType: 'NONE',
      authKeyName: '',
      authKeyValue: '',
      authKeyLocation: 'header',
      authToken: '',
      authUsername: '',
      authPassword: '',
    })
  } finally { submitting.value = false }
}

onMounted(async () => {
  await Promise.all([fetchData(), fetchMcpServers()])
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
</style>
