<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Agent 管理</h2>
      <p class="desc">配置和管理 Agent，支持单 Agent 和编排 Agent</p>
    </div>

    <div class="toolbar">
      <SearchBar v-model="search" placeholder="搜索 Agent 名称..." @search="fetchData" />
      <el-select v-model="filterType" placeholder="全部类型" clearable style="width: 140px" @change="fetchData">
        <el-option label="单 Agent" value="SINGLE" />
        <el-option label="子 Agent" value="SUB" />
        <el-option label="编排 Agent" value="ORCHESTRATOR" />
      </el-select>
      <el-select v-model="filterEnabled" placeholder="全部状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="启用" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 新建 Agent</el-button>
    </div>

    <el-table :data="agents" v-loading="loading" border style="margin-top: 16px">
      <el-table-column label="名称" prop="name" min-width="140">
        <template #default="{ row }">
          <span style="font-weight: 500">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTagType(row.agent_type)">{{ row.agent_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="发布状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'published' ? 'success' : 'info'">
            {{ row.status === 'published' ? '已发布' : '草稿' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="绑定工具" width="90" align="center">
        <template #default="{ row }">
          <span style="color: #666; font-size: 13px">{{ row.tool_ids?.length || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="启用状态" width="100" align="center">
        <template #default="{ row }">
          <StatusTag :enabled="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">配置</el-button>
          <el-button link :type="row.status === 'published' ? 'warning' : 'success'" @click="handlePublish(row)">
            {{ row.status === 'published' ? '下架' : '发布' }}
          </el-button>
          <el-button link :type="row.enabled ? 'warning' : 'success'" @click="handleToggle(row)">
            {{ row.enabled ? '禁用' : '启用' }}
          </el-button>
          <el-popconfirm title="确认删除该 Agent？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <!-- 配置抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="editingId ? `配置 Agent：${form.name}` : '新建 Agent'"
      size="680px"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" style="padding-right: 8px">
        <el-tabs v-model="activeTab">

          <!-- Tab 1: 基础配置 -->
          <el-tab-pane label="基础配置" name="basic">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入 Agent 名称" />
            </el-form-item>
            <el-form-item label="类型" prop="agent_type">
              <el-select v-model="form.agent_type" style="width: 100%">
                <el-option label="单 Agent (SINGLE)" value="SINGLE" />
                <el-option label="子 Agent (SUB)" value="SUB" />
                <el-option label="编排 Agent (ORCHESTRATOR)" value="ORCHESTRATOR" />
              </el-select>
            </el-form-item>
            <el-form-item label="来源平台">
              <el-select v-model="form.source_platform" style="width: 100%">
                <el-option label="本地 (local)" value="local" />
                <el-option label="OpenAI 兼容" value="openai" />
                <el-option label="第三方" value="third-party" />
              </el-select>
            </el-form-item>
            <template v-if="form.source_platform !== 'local'">
              <el-form-item label="访问地址">
                <div style="display:flex;gap:8px;width:100%">
                  <el-input v-model="form.access_url" placeholder="https://api.example.com" style="flex:1" />
                  <el-button :loading="pinging" @click="handlePing">连通测试</el-button>
                </div>
              </el-form-item>
              <el-form-item label="访问令牌">
                <el-input v-model="form.access_token" type="password" show-password />
              </el-form-item>
            </template>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" />
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 2: LLM 模型 -->
          <el-tab-pane label="LLM 模型" name="llm">
            <el-form-item label="绑定模型">
              <el-select v-model="form.llm_model_id" placeholder="选择 LLM 模型" clearable style="width:100%">
                <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="系统提示词">
              <el-input v-model="form.system_prompt" type="textarea" :rows="5" placeholder="输入 system prompt..." />
            </el-form-item>
            <el-form-item label="Temperature">
              <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input style="width:100%" />
            </el-form-item>
            <el-form-item label="Max Tokens">
              <el-input-number v-model="form.max_tokens" :min="256" :max="32768" :step="256" style="width:100%" />
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 3: 意图识别（仅 SINGLE/SUB） -->
          <el-tab-pane v-if="form.agent_type !== 'ORCHESTRATOR'" label="意图识别" name="intent">
            <el-form-item label="启用意图识别">
              <el-switch v-model="form.intent_recognition_enabled" />
            </el-form-item>
            <template v-if="form.intent_recognition_enabled">
              <el-form-item label="识别 LLM">
                <el-select v-model="form.intent_model_id" clearable style="width:100%">
                  <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="置信度阈值">
                <el-slider v-model="form.intent_confidence_threshold" :min="0" :max="1" :step="0.01" show-input style="width:100%" />
              </el-form-item>
              <el-form-item label="系统提示词">
                <el-input v-model="form.intent_system_prompt" type="textarea" :rows="3" />
              </el-form-item>
            </template>
          </el-tab-pane>

          <!-- Tab 4: 工具绑定（仅 SINGLE/SUB） -->
          <el-tab-pane v-if="form.agent_type !== 'ORCHESTRATOR'" label="工具绑定" name="tools">
            <el-form-item label="筛选 Server">
              <el-select v-model="toolFilterServer" clearable placeholder="按 MCP Server 筛选" style="width:100%" @change="filterToolsByServer">
                <el-option v-for="s in mcpServers" :key="s.id" :label="s.display_name || s.name" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="关联工具">
              <el-select v-model="form.tool_ids" multiple collapse-tags collapse-tags-tooltip filterable style="width:100%">
                <el-option v-for="t in filteredTools" :key="t.id" :label="t.display_name || t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 5: 技能绑定（仅 SINGLE/SUB） -->
          <el-tab-pane v-if="form.agent_type !== 'ORCHESTRATOR'" label="技能绑定" name="skills">
            <el-form-item label="关联技能">
              <el-select v-model="form.skill_ids" multiple collapse-tags filterable style="width:100%">
                <el-option v-for="s in allSkills" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 6: 编排器（仅 ORCHESTRATOR） -->
          <el-tab-pane v-if="form.agent_type === 'ORCHESTRATOR'" label="编排器" name="orchestrator">
            <el-form-item label="系统提示词">
              <el-input v-model="form.system_prompt" type="textarea" :rows="5" placeholder="编排 Agent 的系统提示词" />
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 7: 路由配置（仅 ORCHESTRATOR） -->
          <el-tab-pane v-if="form.agent_type === 'ORCHESTRATOR'" label="路由配置" name="routing">
            <el-form-item label="路由策略">
              <el-radio-group v-model="form.routing_strategy">
                <el-radio value="smart">智能路由</el-radio>
                <el-radio value="intent_rule">意图规则路由</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="路由 LLM">
              <el-select v-model="form.routing_model_id" clearable style="width:100%">
                <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-slider v-model="form.routing_threshold" :min="0" :max="1" :step="0.01" show-input style="width:100%" />
            </el-form-item>
            <el-form-item label="路由提示词">
              <el-input v-model="form.routing_system_prompt" type="textarea" :rows="3" />
            </el-form-item>
          </el-tab-pane>

          <!-- Tab 8: 子 Agent（仅 ORCHESTRATOR） -->
          <el-tab-pane v-if="form.agent_type === 'ORCHESTRATOR'" label="子 Agent" name="sub-agents">
            <el-form-item label="子 Agent">
              <el-select v-model="form.sub_agent_ids" multiple collapse-tags filterable style="width:100%">
                <el-option v-for="a in subAgentOptions" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
          </el-tab-pane>

        </el-tabs>
      </el-form>

      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import SearchBar from '@/components/common/SearchBar.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { agentApi, toolApi, skillApi, modelApi, mcpServerApi } from '@/api/index'

const agents = ref<any[]>([])
const allTools = ref<any[]>([])
const allSkills = ref<any[]>([])
const models = ref<any[]>([])
const mcpServers = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const pinging = ref(false)
const search = ref('')
const filterType = ref<string | null>(null)
const filterEnabled = ref<boolean | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const activeTab = ref('basic')
const toolFilterServer = ref<number | null>(null)

const drawerVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()

const form = reactive({
  name: '',
  agent_type: 'SINGLE',
  source_platform: 'local',
  access_url: '',
  access_token: '',
  llm_model_id: null as number | null,
  system_prompt: '',
  description: '',
  tool_ids: [] as number[],
  skill_ids: [] as number[],
  sub_agent_ids: [] as number[],
  status: 'draft',
  temperature: 0.7,
  max_tokens: 2048,
  intent_recognition_enabled: false,
  intent_model_id: null as number | null,
  intent_confidence_threshold: 0.85,
  intent_system_prompt: '',
  routing_strategy: 'smart',
  routing_model_id: null as number | null,
  routing_system_prompt: '',
  routing_threshold: 0.8,
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  agent_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const filteredTools = computed(() => {
  if (!toolFilterServer.value) return allTools.value
  return allTools.value.filter((t: any) => t.mcp_server_id === toolFilterServer.value)
})

const subAgentOptions = computed(() =>
  agents.value.filter(a => a.agent_type === 'SUB' || a.agent_type === 'SINGLE')
)

function filterToolsByServer() {}

function typeTagType(t: string) {
  return t === 'SINGLE' ? '' : t === 'SUB' ? 'warning' : 'danger'
}

async function fetchData() {
  loading.value = true
  try {
    const data: any = await agentApi.list({
      keyword: search.value || undefined,
      agent_type: filterType.value || undefined,
      enabled: filterEnabled.value ?? undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    agents.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchAllTools() {
  const data: any = await toolApi.list({ page_size: 500 })
  allTools.value = data.items || []
}

async function fetchAllSkills() {
  const data: any = await skillApi.list({ page_size: 200 })
  allSkills.value = data.items || []
}

async function fetchModels() {
  const data: any = await modelApi.list({ page_size: 100 })
  models.value = data.items || []
}

async function fetchMcpServers() {
  const data: any = await mcpServerApi.list({ page_size: 100, enabled: true })
  mcpServers.value = data.items || []
}

function resetForm() {
  Object.assign(form, {
    name: '', agent_type: 'SINGLE', source_platform: 'local',
    access_url: '', access_token: '', llm_model_id: null,
    system_prompt: '', description: '', tool_ids: [], skill_ids: [], sub_agent_ids: [],
    status: 'draft', temperature: 0.7, max_tokens: 2048,
    intent_recognition_enabled: false, intent_model_id: null, intent_confidence_threshold: 0.85, intent_system_prompt: '',
    routing_strategy: 'smart', routing_model_id: null, routing_system_prompt: '', routing_threshold: 0.8,
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  activeTab.value = 'basic'
  drawerVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    agent_type: row.agent_type,
    source_platform: row.source_platform || 'local',
    access_url: row.access_url || '',
    access_token: row.access_token || '',
    llm_model_id: row.llm_model_id || null,
    system_prompt: row.system_prompt || '',
    description: row.description || '',
    tool_ids: row.tool_ids || [],
    skill_ids: row.skill_ids || [],
    sub_agent_ids: row.sub_agent_ids || [],
    status: row.status || 'draft',
    temperature: row.temperature ?? 0.7,
    max_tokens: row.max_tokens ?? 2048,
    intent_recognition_enabled: row.intent_recognition_enabled ?? false,
    intent_model_id: row.intent_model_id || null,
    intent_confidence_threshold: row.intent_confidence_threshold ?? 0.85,
    intent_system_prompt: row.intent_system_prompt || '',
    routing_strategy: row.routing_strategy || 'smart',
    routing_model_id: row.routing_model_id || null,
    routing_system_prompt: row.routing_system_prompt || '',
    routing_threshold: row.routing_threshold ?? 0.8,
  })
  activeTab.value = 'basic'
  drawerVisible.value = true
}

async function handlePing() {
  if (!editingId.value) {
    ElMessage.warning('请先保存 Agent 再测试连通性')
    return
  }
  pinging.value = true
  try {
    const res: any = await agentApi.ping(editingId.value)
    if (res?.reachable) {
      ElMessage.success(`连通成功 (${res.latency_ms}ms)`)
    } else {
      ElMessage.error(`连通失败: ${res?.error || '未知错误'}`)
    }
  } finally {
    pinging.value = false
  }
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form }
    if (editingId.value) {
      await agentApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await agentApi.create(payload)
      ElMessage.success('创建成功')
    }
    drawerVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
}

async function handlePublish(row: any) {
  const newStatus = row.status === 'published' ? 'draft' : 'published'
  await agentApi.publish(row.id, newStatus)
  ElMessage.success(newStatus === 'published' ? '已发布' : '已下架')
  fetchData()
}

async function handleToggle(row: any) {
  await agentApi.toggle(row.id, !row.enabled)
  ElMessage.success(row.enabled ? '已禁用' : '已启用')
  fetchData()
}

async function handleDelete(id: number) {
  await agentApi.delete(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(() => {
  fetchData()
  fetchAllTools()
  fetchAllSkills()
  fetchModels()
  fetchMcpServers()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
</style>
