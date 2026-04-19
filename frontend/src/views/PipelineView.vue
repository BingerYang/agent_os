<template>
  <div class="page-container">
    <div class="page-header">
      <h2>检测规则管理</h2>
      <p class="desc">管理前置与后置 DetectionRule，支持关键字匹配与 LLM 判定</p>
    </div>

    <div class="toolbar">
      <SearchBar v-model="search" placeholder="搜索规则名称..." @search="handleSearch" />
      <el-select
        v-model="filterStage"
        placeholder="全部阶段"
        clearable
        style="width: 140px"
        @change="handleFilterChange"
      >
        <el-option label="pre" value="PRE" />
        <el-option label="post" value="POST" />
      </el-select>
      <el-select
        v-model="filterType"
        placeholder="全部类型"
        clearable
        style="width: 160px"
        @change="handleFilterChange"
      >
        <el-option label="keyword" value="keyword" />
        <el-option label="llm_judge" value="llm_judge" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 新建规则</el-button>
    </div>

    <el-table :data="ruleList" v-loading="loading" border style="margin-top: 16px">
      <el-table-column label="名称" prop="name" min-width="180">
        <template #default="{ row }">
          <span class="primary-text">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Stage" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.stage === 'PRE' ? 'primary' : 'warning'">
            {{ stageLabel(row.stage) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Rule Type" width="130" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.rule_type === 'keyword' ? 'info' : 'success'">
            {{ row.rule_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <StatusTag :enabled="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="描述" min-width="320" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ getDescription(row) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除该规则？" @confirm="handleDelete(row.id)">
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
      :title="editingId ? '编辑规则' : '新建规则'"
      width="640px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="Stage" prop="stage">
          <el-select v-model="form.stage" style="width: 100%">
            <el-option label="pre" value="PRE" />
            <el-option label="post" value="POST" />
          </el-select>
        </el-form-item>
        <el-form-item label="Rule Type" prop="rule_type">
          <el-select v-model="form.rule_type" style="width: 100%">
            <el-option label="keyword" value="keyword" />
            <el-option label="llm_judge" value="llm_judge" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入规则用途或补充说明"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <template v-if="form.rule_type === 'keyword'">
          <el-form-item label="Pattern">
            <el-input
              v-model="form.keywordPattern"
              type="textarea"
              :rows="4"
              placeholder="输入关键字或正则，每行一条"
            />
            <div class="field-tip">支持普通关键字和正则表达式，例如：`(?i)(赌博|欺诈)`</div>
          </el-form-item>
          <el-form-item label="Action">
            <el-select v-model="form.keywordAction" style="width: 100%">
              <el-option label="block" value="block" />
              <el-option label="warn" value="warn" />
              <el-option label="log" value="log" />
            </el-select>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="Prompt" prop="prompt_template">
            <el-input
              v-model="form.promptTemplate"
              type="textarea"
              :rows="6"
              placeholder="输入 prompt template，使用 {text} 作为待检测内容占位符"
            />
          </el-form-item>
          <el-form-item label="Threshold">
            <el-slider
              v-model="form.threshold"
              :min="0"
              :max="1"
              :step="0.01"
              show-input
              input-size="small"
            />
          </el-form-item>
        </template>
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
import { detectionRuleApi } from '@/api/index'

type RuleStage = 'PRE' | 'POST'
type RuleType = 'keyword' | 'llm_judge'
type KeywordAction = 'block' | 'warn' | 'log'

interface DetectionRuleRow {
  id: number
  name: string
  stage: RuleStage
  rule_type: RuleType
  rule_content?: Record<string, unknown>
  reject_message?: string
  enabled: boolean
}

interface DetectionRuleForm {
  name: string
  stage: RuleStage
  rule_type: RuleType
  description: string
  enabled: boolean
  keywordPattern: string
  keywordAction: KeywordAction
  promptTemplate: string
  threshold: number
}

const ruleList = ref<DetectionRuleRow[]>([])
const loading = ref(false)
const submitting = ref(false)
const search = ref('')
const filterStage = ref<RuleStage | null>(null)
const filterType = ref<RuleType | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<DetectionRuleForm>({
  name: '',
  stage: 'PRE',
  rule_type: 'keyword',
  description: '',
  enabled: true,
  keywordPattern: '',
  keywordAction: 'block',
  promptTemplate: '判断以下内容是否违规，请仅回答 yes 或 no：{text}',
  threshold: 0.8,
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  stage: [{ required: true, message: '请选择阶段', trigger: 'change' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
}

async function fetchData() {
  loading.value = true
  try {
    const data = await detectionRuleApi.list({
      keyword: search.value || undefined,
      stage: filterStage.value || undefined,
      rule_type: filterType.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    }) as { items?: DetectionRuleRow[]; total?: number }

    ruleList.value = data.items || []
    total.value = data.total || 0
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    stage: 'PRE',
    rule_type: 'keyword',
    description: '',
    enabled: true,
    keywordPattern: '',
    keywordAction: 'block',
    promptTemplate: '判断以下内容是否违规，请仅回答 yes 或 no：{text}',
    threshold: 0.8,
  })
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row: DetectionRuleRow) {
  const ruleContent = row.rule_content || {}
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    stage: row.stage,
    rule_type: row.rule_type,
    description: getRuleContentText(ruleContent.description),
    enabled: row.enabled,
    keywordPattern: extractPatterns(ruleContent).join('\n'),
    keywordAction: normalizeKeywordAction(ruleContent.action),
    promptTemplate: getRuleContentText(ruleContent.prompt_template || ruleContent.prompt),
    threshold: normalizeThreshold(ruleContent.threshold),
  })
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

async function handleSubmit() {
  await formRef.value?.validate()

  if (form.rule_type === 'keyword' && !form.keywordPattern.trim()) {
    ElMessage.warning('请输入 Pattern')
    return
  }

  if (form.rule_type === 'llm_judge' && !form.promptTemplate.trim()) {
    ElMessage.warning('请输入 Prompt Template')
    return
  }

  submitting.value = true
  try {
    const payload = buildPayload()

    if (editingId.value) {
      await detectionRuleApi.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      const created = await detectionRuleApi.create(removeEnabledForCreate(payload)) as DetectionRuleRow
      if (!form.enabled) {
        await detectionRuleApi.toggle(created.id, false)
      }
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  await detectionRuleApi.delete(id)
  ElMessage.success('删除成功')

  if (ruleList.value.length === 1 && page.value > 1) {
    page.value -= 1
  }

  await fetchData()
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function handleFilterChange() {
  page.value = 1
  fetchData()
}

function buildPayload() {
  if (form.rule_type === 'keyword') {
    return {
      name: form.name.trim(),
      stage: form.stage,
      rule_type: form.rule_type,
      enabled: form.enabled,
      rule_content: compactObject({
        description: form.description.trim(),
        patterns: form.keywordPattern
          .split('\n')
          .map(item => item.trim())
          .filter(Boolean),
        action: form.keywordAction,
      }),
    }
  }

  return {
    name: form.name.trim(),
    stage: form.stage,
    rule_type: form.rule_type,
    enabled: form.enabled,
    rule_content: compactObject({
      description: form.description.trim(),
      prompt: form.promptTemplate.trim(),
      prompt_template: form.promptTemplate.trim(),
      threshold: form.threshold,
    }),
  }
}

function removeEnabledForCreate(payload: Record<string, unknown>) {
  const { enabled, ...rest } = payload
  return rest
}

function compactObject(source: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(source).filter(([, value]) => {
      if (value === null || value === undefined) return false
      if (typeof value === 'string') return value.trim() !== ''
      if (Array.isArray(value)) return value.length > 0
      return true
    })
  )
}

function extractPatterns(ruleContent: Record<string, unknown>) {
  const patterns = Array.isArray(ruleContent.patterns) ? ruleContent.patterns : []
  const keywords = Array.isArray(ruleContent.keywords) ? ruleContent.keywords : []
  const source = patterns.length ? patterns : keywords

  return source
    .map(item => typeof item === 'string' ? item : '')
    .filter(Boolean)
}

function normalizeKeywordAction(action: unknown): KeywordAction {
  return action === 'warn' || action === 'log' ? action : 'block'
}

function normalizeThreshold(value: unknown) {
  return typeof value === 'number' && value >= 0 && value <= 1 ? value : 0.8
}

function getRuleContentText(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function getDescription(row: DetectionRuleRow) {
  const ruleContent = row.rule_content || {}
  const description = getRuleContentText(ruleContent.description)
  if (description) return description

  if (row.rule_type === 'keyword') {
    const patterns = extractPatterns(ruleContent)
    return patterns.length ? patterns.join(' / ') : '-'
  }

  const prompt = getRuleContentText(ruleContent.prompt_template || ruleContent.prompt)
  return prompt || '-'
}

function stageLabel(stage: RuleStage) {
  return stage === 'PRE' ? 'pre' : 'post'
}

onMounted(fetchData)
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.primary-text { font-weight: 500; }
.field-tip { margin-top: 6px; color: #909399; font-size: 12px; line-height: 1.5; }
</style>
