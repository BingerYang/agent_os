<template>
  <div class="page-container">
    <div class="page-header">
      <h2>模型配置</h2>
      <p class="desc">配置 Agent 调用所需的模型 API Key，配置后加密存储</p>
    </div>

    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索模型名称、供应商..." clearable style="width: 260px" />
      <el-select v-model="filterSupplier" placeholder="全部供应商" clearable style="width: 160px">
        <el-option v-for="s in suppliers" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 140px">
        <el-option label="已配置" value="configured" />
        <el-option label="未配置" value="unconfigured" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 新建配置</el-button>
    </div>

    <el-table :data="models" v-loading="loading" border style="margin-top: 16px">
      <el-table-column type="selection" width="50" />
      <el-table-column label="模型名称" prop="name" min-width="140">
        <template #default="{ row }">
          <span style="font-weight: 500">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="供应商 / 类别" min-width="160">
        <template #default="{ row }">
          <span style="color: #666; font-size: 13px">{{ row.supplier }} / {{ row.category }}</span>
        </template>
      </el-table-column>
      <el-table-column label="API 标识" prop="model_id" min-width="160" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '已配置' : '未配置' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除该模型配置？" @confirm="handleDelete(row.id)">
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
      @change="fetchModels"
    />

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑配置' : '新建配置'" width="560px">
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="模型名称" prop="name">
          <el-input v-model="form.name" placeholder="如：业务专属模型" />
        </el-form-item>
        <el-form-item label="API 标识" prop="model_id">
          <el-input v-model="form.model_id" placeholder="英文唯一标识，如：gpt-4-turbo" :disabled="!!editingId" />
        </el-form-item>
        <el-form-item label="供应商" prop="supplier">
          <el-select v-model="form.supplier" style="width: 100%">
            <el-option v-for="s in suppliers" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型类别" prop="category">
          <el-input v-model="form.category" placeholder="如：GPT系列" />
        </el-form-item>
        <el-form-item label="API Endpoint">
          <el-input v-model="form.endpoint_url" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="请输入 API Key" />
          <div style="font-size: 12px; color: #999; margin-top: 4px">配置后加密存储，列表中显示为脱敏格式</div>
        </el-form-item>
        <el-form-item label="API 版本标识">
          <el-input v-model="form.api_version" placeholder="如：gpt-4-turbo" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi } from '@/api'

const suppliers = ['阿里云', 'OpenAI', 'DeepSeek', '字节跳动', '百度', '自定义']

const loading = ref(false)
const submitting = ref(false)
const models = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const search = ref('')
const filterSupplier = ref('')
const filterStatus = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()

const form = reactive({
  name: '', model_id: '', supplier: '阿里云', category: '',
  endpoint_url: '', api_key: '', api_version: '', description: ''
})

const rules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_id: [{ required: true, message: '请输入 API 标识', trigger: 'blur' }],
  supplier: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  category: [{ required: true, message: '请输入模型类别', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }]
}

async function fetchModels() {
  loading.value = true
  try {
    const res: any = await modelApi.list({ keyword: search.value || undefined, supplier: filterSupplier.value || undefined, page: page.value, page_size: pageSize.value })
    models.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', model_id: '', supplier: '阿里云', category: '', endpoint_url: '', api_key: '', api_version: '', description: '' })
  dialogVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, { ...row, api_key: '' })
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editingId.value) {
      const data = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''))
      await modelApi.update(editingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await modelApi.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchModels()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  await modelApi.delete(id)
  ElMessage.success('删除成功')
  fetchModels()
}

watch([search, filterSupplier, filterStatus], () => { page.value = 1; fetchModels() })
onMounted(fetchModels)
</script>

<style scoped>
.page-container { padding: 24px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0 0 4px; font-size: 20px; }
.desc { margin: 0; color: #666; font-size: 13px; }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
</style>
