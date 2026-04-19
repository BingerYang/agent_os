<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Agent 管理</h2>
      <p class="desc">配置和管理 SINGLE 类型 Agent，绑定模型与工具</p>
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
      <el-table-column label="绑定工具" min-width="160">
        <template #default="{ row }">
          <span style="color: #666; font-size: 13px">{{ row.tool_ids?.length || 0 }} 个工具</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusTag :enabled="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 Agent' : '新建 Agent'" width="600px" destroy-on-close>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
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
            <div style="display: flex; gap: 8px; width: 100%">
              <el-input v-model="form.access_url" placeholder="https://api.example.com" style="flex: 1" />
              <el-button :loading="pinging" @click="handlePing">连通性测试</el-button>
            </div>
          </el-form-item>
          <el-form-item label="访问令牌">
            <el-input v-model="form.access_token" type="password" show-password placeholder="Bearer token 或 API key" />
          </el-form-item>
        </template>
        <el-form-item label="绑定模型" prop="llm_model_id">
          <el-select v-model="form.llm_model_id" placeholder="选择 LLM 模型" clearable style="width: 100%">
            <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input v-model="form.system_prompt" type="textarea" :rows="4" placeholder="输入 system prompt..." />
        </el-form-item>
        <el-form-item label="关联工具">
          <el-select v-model="form.tool_ids" multiple placeholder="选择关联工具" style="width: 100%">
            <el-option v-for="t in allTools" :key="t.id" :label="t.display_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
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
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import SearchBar from '@/components/common/SearchBar.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { agentApi, toolApi, modelApi } from '@/api/index'

const agents = ref<any[]>([])
const allTools = ref<any[]>([])
const models = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const pinging = ref(false)
const search = ref('')
const filterType = ref<string | null>(null)
const filterEnabled = ref<boolean | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
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
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  agent_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

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
  const data: any = await toolApi.list({ page_size: 200 })
  allTools.value = data.items || []
}

async function fetchModels() {
  const data: any = await modelApi.list({ page_size: 100 })
  models.value = data.items || []
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: '',
    agent_type: 'SINGLE',
    source_platform: 'local',
    access_url: '',
    access_token: '',
    llm_model_id: null,
    system_prompt: '',
    description: '',
    tool_ids: [],
    skill_ids: [],
  })
  dialogVisible.value = true
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
  })
  dialogVisible.value = true
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
    if (editingId.value) {
      await agentApi.update(editingId.value, { ...form })
      ElMessage.success('更新成功')
    } else {
      await agentApi.create({ ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    submitting.value = false
  }
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
  fetchModels()
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
</style>
