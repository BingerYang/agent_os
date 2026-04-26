<template>
  <div class="page-container">
    <div class="page-header">
      <h2>插件广场</h2>
      <p class="desc">浏览、安装和卸载 Tool / Skill / Agent 子系统</p>
    </div>

    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">工具</span>
        <span class="stat-value">{{ stats.tool.installed }} / {{ stats.tool.total }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">技能</span>
        <span class="stat-value">{{ stats.skill.installed }} / {{ stats.skill.total }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">Agent</span>
        <span class="stat-value">{{ stats.agent.installed }} / {{ stats.agent.total }}</span>
      </div>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索名称..." clearable style="width: 220px" @keyup.enter="fetchData" @clear="fetchData" />
      <el-select v-model="filterType" placeholder="全部类型" clearable style="width: 130px" @change="fetchData">
        <el-option label="工具" value="tool" />
        <el-option label="技能" value="skill" />
        <el-option label="Agent" value="agent" />
      </el-select>
      <el-select v-model="filterEnabled" placeholder="全部状态" clearable style="width: 120px" @change="fetchData">
        <el-option label="已安装" :value="true" />
        <el-option label="未安装" :value="false" />
      </el-select>
      <el-button :icon="Refresh" @click="fetchData">刷新</el-button>
      <el-dropdown @command="handleAddCommand">
        <el-button type="primary">
          + 添加&nbsp;<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="tool">添加工具 (Tool)</el-dropdown-item>
            <el-dropdown-item command="skill">添加技能 (Skill)</el-dropdown-item>
            <el-dropdown-item command="agent">注册第三方 Agent</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div v-loading="loading" class="card-grid">
      <MarketplaceCard
        v-for="item in items"
        :key="`${item.item_type}-${item.id}`"
        :item="item"
        :loading="Boolean(installing[`${item.item_type}_${item.id}`])"
        @toggle="handleToggle"
        @delete="handleDelete"
      />
      <el-empty v-if="!loading && items.length === 0" description="暂无条目" style="grid-column: 1 / -1" />
    </div>

    <el-dialog v-model="registerAgentVisible" title="注册第三方 Agent" width="500px" destroy-on-close>
      <el-form :model="agentForm" :rules="agentRules" ref="agentFormRef" label-width="100px">
        <el-form-item label="名称" prop="name"><el-input v-model="agentForm.name" /></el-form-item>
        <el-form-item label="访问地址" prop="access_url"><el-input v-model="agentForm.access_url" placeholder="https://..." /></el-form-item>
        <el-form-item label="访问令牌"><el-input v-model="agentForm.access_token" type="password" show-password /></el-form-item>
        <el-form-item label="描述"><el-input v-model="agentForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerAgentVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleRegisterAgent">注册</el-button>
      </template>
    </el-dialog>

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

    <el-dialog v-model="addSkillVisible" title="添加技能 (Skill)" width="500px" destroy-on-close>
      <el-form :model="skillForm" :rules="skillRules" ref="skillFormRef" label-width="100px">
        <el-form-item label="名称" prop="name"><el-input v-model="skillForm.name" placeholder="唯一标识，如 summarize" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="skillForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="触发条件"><el-input v-model="skillForm.trigger_condition" type="textarea" :rows="2" placeholder="描述何时触发此技能" /></el-form-item>
        <el-form-item label="标签"><el-input v-model="skillForm.tagsRaw" placeholder="逗号分隔，如: nlp,text" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addSkillVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddSkill">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Refresh, ArrowDown } from '@element-plus/icons-vue'
import MarketplaceCard from '@/components/marketplace/MarketplaceCard.vue'
import type { MarketplaceItemType, MarketplaceTogglePayload } from '@/stores/marketplace'
import { useMarketplaceStore } from '@/stores/marketplace'
import { storeToRefs } from 'pinia'

const store = useMarketplaceStore()
const { items, loading, installing } = storeToRefs(store)

const keyword = ref('')
const filterType = ref<MarketplaceItemType | null>(null)
const filterEnabled = ref<boolean | null>(null)
const submitting = ref(false)

const stats = computed(() => {
  const result = {
    tool: { total: 0, installed: 0 },
    skill: { total: 0, installed: 0 },
    agent: { total: 0, installed: 0 },
  }
  for (const item of items.value) {
    const t = result[item.item_type]
    if (t) { t.total++; if (item.enabled) t.installed++ }
  }
  return result
})

const registerAgentVisible = ref(false)
const agentFormRef = ref()
const agentForm = reactive({ name: '', access_url: '', access_token: '', description: '' })
const agentRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  access_url: [{ required: true, message: '请输入访问地址', trigger: 'blur' }],
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

const addSkillVisible = ref(false)
const skillFormRef = ref()
const skillForm = reactive({ name: '', description: '', trigger_condition: '', tagsRaw: '' })
const skillRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

function handleAddCommand(cmd: string) {
  if (cmd === 'agent') registerAgentVisible.value = true
  else if (cmd === 'tool') addToolVisible.value = true
  else if (cmd === 'skill') addSkillVisible.value = true
}

async function fetchData() {
  await store.fetchItems({
    item_type: filterType.value || undefined,
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

async function handleRegisterAgent() {
  await agentFormRef.value.validate()
  submitting.value = true
  try {
    await store.registerAgent({ ...agentForm })
    await fetchData()
    registerAgentVisible.value = false
    Object.assign(agentForm, { name: '', access_url: '', access_token: '', description: '' })
  } finally { submitting.value = false }
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

async function handleAddSkill() {
  await skillFormRef.value.validate()
  submitting.value = true
  try {
    const tags = skillForm.tagsRaw ? skillForm.tagsRaw.split(',').map((t) => t.trim()).filter(Boolean) : []
    await store.createSkill({ name: skillForm.name, description: skillForm.description || undefined, trigger_condition: skillForm.trigger_condition || undefined, tags })
    await fetchData()
    addSkillVisible.value = false
    Object.assign(skillForm, { name: '', description: '', trigger_condition: '', tagsRaw: '' })
  } finally { submitting.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.stats-bar { display: flex; gap: 16px; margin-bottom: 16px; }
.stat-item { background: white; border-radius: 6px; padding: 10px 20px; display: flex; flex-direction: column; align-items: center; min-width: 100px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.stat-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.stat-value { font-size: 18px; font-weight: 600; color: #303133; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 20px; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
</style>
