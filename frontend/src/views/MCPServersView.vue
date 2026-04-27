<template>
  <div class="page-container">
    <div class="page-header">
      <h2>MCP 服务</h2>
      <p class="desc">管理 MCP Server 连接配置，自动发现并注册工具</p>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索名称..." clearable style="width: 220px" @keyup.enter="fetchData" @clear="fetchData" />
      <el-select v-model="filterEnabled" placeholder="全部状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="已启用" :value="true" />
        <el-option label="已禁用" :value="false" />
      </el-select>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
      <el-button type="primary" @click="openCreate">+ 新增 MCP Server</el-button>
    </div>

    <div v-loading="store.loading" class="card-grid">
      <el-card
        v-for="server in store.servers"
        :key="server.id"
        class="server-card"
        :class="{ disabled: !server.enabled }"
        shadow="hover"
      >
        <div class="card-header">
          <span class="server-name">{{ server.display_name || server.name }}</span>
          <el-tag size="small" :type="statusTagType(server.status)">{{ server.status }}</el-tag>
        </div>
        <div class="card-meta">
          <el-tag size="small" effect="plain">{{ server.transport_type }}</el-tag>
          <span class="muted">{{ server.description || '暂无描述' }}</span>
        </div>
        <div v-if="server.last_connected_at" class="muted small">
          最后连接：{{ formatDateTime(server.last_connected_at) }}
        </div>
        <div class="card-actions">
          <el-button size="small" @click="handleConnect(server)" :loading="connecting[server.id]">测试连接</el-button>
          <el-button size="small" @click="handleDiscover(server)" :loading="discovering[server.id]">发现工具</el-button>
          <el-button size="small" type="primary" @click="openEdit(server)">编辑</el-button>
          <el-switch
            :model-value="server.enabled"
            size="small"
            @change="(v: boolean) => handleToggle(server, v)"
          />
          <el-popconfirm title="确认删除该 MCP Server？" @confirm="handleDelete(server.id)">
            <template #reference>
              <el-button size="small" type="danger" text :icon="Delete" />
            </template>
          </el-popconfirm>
        </div>
      </el-card>
      <el-empty v-if="!store.loading && store.servers.length === 0" description="暂无 MCP Server" style="grid-column: 1 / -1" />
    </div>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="store.total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 MCP Server' : '新增 MCP Server'"
      width="600px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="唯一标识，如 puppeteer" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="友好展示名称" />
        </el-form-item>
        <el-form-item label="传输类型" prop="transport_type">
          <el-radio-group v-model="form.transport_type">
            <el-radio value="HTTP_SSE">HTTP / SSE</el-radio>
            <el-radio value="STDIO">STDIO</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- STDIO 模式 -->
        <template v-if="form.transport_type === 'STDIO'">
          <el-form-item label="启动命令" prop="command">
            <el-input v-model="form.command" placeholder="如 npx -y @modelcontextprotocol/server-puppeteer" />
          </el-form-item>
          <el-form-item label="环境变量">
            <div class="kv-editor">
              <div v-for="(kv, idx) in form.envList" :key="idx" class="kv-row">
                <el-input v-model="kv.key" placeholder="KEY" style="width: 140px" />
                <el-input v-model="kv.value" placeholder="VALUE" style="flex: 1" show-password />
                <el-button text :icon="Delete" @click="form.envList.splice(idx, 1)" />
              </div>
              <el-button size="small" @click="form.envList.push({ key: '', value: '' })">+ 添加</el-button>
            </div>
          </el-form-item>
        </template>

        <!-- HTTP_SSE 模式 -->
        <template v-if="form.transport_type === 'HTTP_SSE'">
          <el-form-item label="服务地址" prop="endpoint_url">
            <el-input v-model="form.endpoint_url" placeholder="https://mcp.example.com/sse" />
          </el-form-item>
          <el-form-item label="认证方式">
            <el-select v-model="form.auth_type" style="width: 100%">
              <el-option label="无认证" value="NONE" />
              <el-option label="API Key" value="API_KEY" />
              <el-option label="Bearer Token" value="BEARER_TOKEN" />
              <el-option label="Basic Auth" value="BASIC_AUTH" />
            </el-select>
          </el-form-item>
          <template v-if="form.auth_type === 'API_KEY'">
            <el-form-item label="Key 名称"><el-input v-model="form.authKeyName" placeholder="如 X-API-Key" /></el-form-item>
            <el-form-item label="Key 值"><el-input v-model="form.authKeyValue" show-password /></el-form-item>
            <el-form-item label="传递位置">
              <el-radio-group v-model="form.authKeyLocation">
                <el-radio value="header">Header</el-radio>
                <el-radio value="query">Query</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>
          <el-form-item v-if="form.auth_type === 'BEARER_TOKEN'" label="Token">
            <el-input v-model="form.authToken" show-password />
          </el-form-item>
          <template v-if="form.auth_type === 'BASIC_AUTH'">
            <el-form-item label="用户名"><el-input v-model="form.authUsername" /></el-form-item>
            <el-form-item label="密码"><el-input v-model="form.authPassword" type="password" show-password /></el-form-item>
          </template>
        </template>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Delete } from '@element-plus/icons-vue'
import { useMCPServersStore, type MCPServer } from '@/stores/mcpServers'

const store = useMCPServersStore()

const keyword = ref('')
const filterEnabled = ref<boolean | null>(null)
const page = ref(1)
const pageSize = ref(20)
const submitting = ref(false)
const connecting = ref<Record<number, boolean>>({})
const discovering = ref<Record<number, boolean>>({})

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()

interface KV { key: string; value: string }

const form = reactive({
  name: '',
  display_name: '',
  description: '',
  transport_type: 'HTTP_SSE' as 'HTTP_SSE' | 'STDIO',
  command: '',
  endpoint_url: '',
  auth_type: 'NONE',
  authKeyName: '',
  authKeyValue: '',
  authKeyLocation: 'header',
  authToken: '',
  authUsername: '',
  authPassword: '',
  enabled: true,
  envList: [] as KV[],
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  transport_type: [{ required: true }],
}

function statusTagType(status: string) {
  if (status === 'CONNECTED') return 'success'
  if (status === 'ERROR') return 'danger'
  if (status === 'DISCONNECTED') return 'warning'
  return 'info'
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN', { hour12: false })
}

async function fetchData() {
  await store.fetchServers({
    keyword: keyword.value || undefined,
    enabled: filterEnabled.value ?? undefined,
    page: page.value,
    page_size: pageSize.value,
  })
}

function resetForm() {
  Object.assign(form, {
    name: '', display_name: '', description: '',
    transport_type: 'HTTP_SSE', command: '', endpoint_url: '',
    auth_type: 'NONE', authKeyName: '', authKeyValue: '', authKeyLocation: 'header',
    authToken: '', authUsername: '', authPassword: '', enabled: true, envList: [],
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEdit(server: MCPServer) {
  editingId.value = server.id
  const envList: KV[] = server.env_vars
    ? Object.entries(server.env_vars).map(([key, value]) => ({ key, value }))
    : []
  let authKeyName = '', authKeyValue = '', authKeyLocation = 'header', authToken = '', authUsername = '', authPassword = ''
  if (server.auth_config) {
    authKeyName = server.auth_config.key_name || ''
    authKeyValue = server.auth_config.key_value || ''
    authKeyLocation = server.auth_config.key_location || 'header'
    authToken = server.auth_config.token || ''
    authUsername = server.auth_config.username || ''
    authPassword = server.auth_config.password || ''
  }
  Object.assign(form, {
    name: server.name, display_name: server.display_name, description: server.description || '',
    transport_type: server.transport_type, command: server.command || '', endpoint_url: server.endpoint_url || '',
    auth_type: server.auth_type, authKeyName, authKeyValue, authKeyLocation, authToken, authUsername, authPassword,
    enabled: server.enabled, envList,
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const env_vars = form.envList.reduce((acc: Record<string, string>, kv) => {
      if (kv.key.trim()) acc[kv.key.trim()] = kv.value
      return acc
    }, {})
    let auth_config: Record<string, string> | null = null
    if (form.auth_type === 'API_KEY') {
      auth_config = { key_name: form.authKeyName, key_value: form.authKeyValue, key_location: form.authKeyLocation }
    } else if (form.auth_type === 'BEARER_TOKEN') {
      auth_config = { token: form.authToken }
    } else if (form.auth_type === 'BASIC_AUTH') {
      auth_config = { username: form.authUsername, password: form.authPassword }
    }
    const payload: Record<string, unknown> = {
      name: form.name, display_name: form.display_name, description: form.description || undefined,
      transport_type: form.transport_type, enabled: form.enabled, auth_type: form.auth_type, auth_config,
    }
    if (form.transport_type === 'STDIO') {
      payload.command = form.command
      payload.env_vars = Object.keys(env_vars).length ? env_vars : null
    } else {
      payload.endpoint_url = form.endpoint_url
    }
    if (editingId.value) {
      await store.updateServer(editingId.value, payload)
    } else {
      await store.createServer(payload)
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleToggle(server: MCPServer, enabled: boolean) {
  await store.toggleServer(server.id, enabled)
  await fetchData()
}

async function handleDelete(id: number) {
  await store.deleteServer(id)
}

async function handleConnect(server: MCPServer) {
  connecting.value[server.id] = true
  try {
    const result = await store.connectServer(server.id)
    if (result.status === 'CONNECTED') {
      ElMessage.success(`连接成功 (${result.latency_ms}ms)`)
    } else {
      ElMessage.error(`连接失败: ${result.error || '未知错误'}`)
    }
    await fetchData()
  } finally {
    delete connecting.value[server.id]
  }
}

async function handleDiscover(server: MCPServer) {
  discovering.value[server.id] = true
  try {
    const result = await store.discoverTools(server.id)
    ElMessage.info(`${result.message}（新增 ${result.new_tools} 个工具）`)
  } finally {
    delete discovering.value[server.id]
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.server-card { transition: transform 0.2s ease; }
.server-card:hover { transform: translateY(-2px); }
.server-card.disabled { opacity: 0.7; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.server-name { font-size: 15px; font-weight: 600; color: #303133; }
.card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.muted { color: #909399; font-size: 13px; }
.small { font-size: 12px; margin-bottom: 8px; }
.card-actions { display: flex; align-items: center; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #ebeef5; flex-wrap: wrap; }
.kv-editor { width: 100%; }
.kv-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
</style>
