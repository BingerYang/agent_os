<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Skill 管理</h2>
      <p class="desc">管理 Skill 基础信息，并为 Skill 绑定可调用工具</p>
    </div>

    <div class="toolbar">
      <SearchBar v-model="search" placeholder="搜索 Skill 名称..." @search="handleSearch" />
      <el-select v-model="filterCategory" placeholder="全部分类" clearable style="width: 140px" @change="handleSearch">
        <el-option label="通用" value="general" />
        <el-option label="场景技能" value="scene" />
        <el-option label="基础技能" value="basic" />
        <el-option label="安全技能" value="security" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 新建 Skill</el-button>
    </div>

    <el-table :data="skills" v-loading="loading" border style="margin-top: 16px">
      <el-table-column label="名称" prop="name" min-width="160">
        <template #default="{ row }">
          <span class="primary-text">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="描述" prop="description" min-width="260" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.description || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.category || 'general' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="版本" width="90" align="center">
        <template #default="{ row }">
          <span class="muted-text">{{ row.version || 'v1.0.0' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="作者" width="110" align="center">
        <template #default="{ row }">
          <span class="muted-text">{{ row.author || '系统官方' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="关联工具数量" width="120" align="center">
        <template #default="{ row }">
          <span class="muted-text">{{ row.tool_ids?.length || 0 }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <StatusTag :enabled="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">
          <span class="muted-text">{{ formatDateTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除该 Skill？" @confirm="handleDelete(row.id)">
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

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑 Skill' : '新建 Skill'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入 Skill 名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入 Skill 描述"
          />
        </el-form-item>
        <el-form-item label="触发条件">
          <el-input
            v-model="form.trigger_condition"
            type="textarea"
            :rows="2"
            placeholder="描述何时触发此技能"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="通用" value="general" />
            <el-option label="场景技能" value="scene" />
            <el-option label="基础技能" value="basic" />
            <el-option label="安全技能" value="security" />
          </el-select>
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="form.author" placeholder="来源/作者标识" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="form.version" placeholder="如 v1.0.0" />
        </el-form-item>
        <el-form-item label="关联工具">
          <el-select
            v-model="form.tool_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="从工具列表中选择"
            style="width: 100%"
          >
            <el-option
              v-for="tool in toolOptions"
              :key="tool.id"
              :label="tool.display_name || tool.name"
              :value="tool.id"
            />
          </el-select>
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
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import SearchBar from '@/components/common/SearchBar.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { skillApi, toolApi } from '@/api/index'

interface ToolOption {
  id: number
  name: string
  display_name?: string
}

interface SkillRow {
  id: number
  name: string
  description?: string
  trigger_condition?: string
  category?: string
  author?: string
  version?: string
  tool_ids: number[]
  enabled: boolean
  created_at?: string
}

interface SkillForm {
  name: string
  description: string
  trigger_condition: string
  category: string
  author: string
  version: string
  tool_ids: number[]
}

const skills = ref<SkillRow[]>([])
const toolOptions = ref<ToolOption[]>([])
const loading = ref(false)
const submitting = ref(false)
const search = ref('')
const filterCategory = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<SkillForm>({
  name: '',
  description: '',
  trigger_condition: '',
  category: 'general',
  author: '系统官方',
  version: 'v1.0.0',
  tool_ids: [],
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const data = await skillApi.list({
      keyword: search.value || undefined,
      category: filterCategory.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    }) as { items?: SkillRow[]; total?: number }

    skills.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

async function fetchTools() {
  const data = await toolApi.list({ page_size: 200 }) as { items?: ToolOption[] }
  toolOptions.value = data.items || []
}

function resetForm() {
  Object.assign(form, {
    name: '',
    description: '',
    trigger_condition: '',
    category: 'general',
    author: '系统官方',
    version: 'v1.0.0',
    tool_ids: [],
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: SkillRow) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    description: row.description || '',
    tool_ids: [...(row.tool_ids || [])],
    trigger_condition: row.trigger_condition || '',
    category: row.category || 'general',
    author: row.author || '系统官方',
    version: row.version || 'v1.0.0',
  })
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

async function handleSubmit() {
  await formRef.value?.validate()

  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      tool_ids: [...form.tool_ids],
      trigger_condition: form.trigger_condition.trim() || undefined,
      category: form.category,
      author: form.author.trim() || undefined,
      version: form.version.trim() || undefined,
    }

    if (editingId.value) {
      await skillApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await skillApi.create(payload)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  await skillApi.delete(id)
  ElMessage.success('删除成功')

  if (skills.value.length === 1 && page.value > 1) {
    page.value -= 1
  }

  await fetchData()
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function formatDateTime(value?: string) {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  await Promise.all([fetchData(), fetchTools()])
})
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.primary-text { font-weight: 500; }
.muted-text { color: #666; font-size: 13px; }
</style>
