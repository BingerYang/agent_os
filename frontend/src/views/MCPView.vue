<template>
  <div class="page-container">
    <div class="page-header">
      <h2>插件广场</h2>
      <p class="desc">浏览、安装和卸载 Tool/Skill/Agent 子系统</p>
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
      <el-button type="primary" @click="registerDialogVisible = true">+ 注册第三方 Agent</el-button>
    </div>

    <div v-loading="loading" class="card-grid">
      <MarketplaceCard
        v-for="item in items"
        :key="`${item.item_type}-${item.id}`"
        :item="item"
        :loading="Boolean(installing[`${item.item_type}_${item.id}`])"
        @toggle="handleToggle"
      />
      <el-empty v-if="!loading && items.length === 0" description="暂无条目" style="grid-column: 1 / -1" />
    </div>

    <!-- 注册第三方 Agent 弹窗 -->
    <el-dialog v-model="registerDialogVisible" title="注册第三方 Agent" width="500px" destroy-on-close>
      <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="registerForm.name" />
        </el-form-item>
        <el-form-item label="访问地址" prop="access_url">
          <el-input v-model="registerForm.access_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="访问令牌">
          <el-input v-model="registerForm.access_token" type="password" show-password />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="registerForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="registering" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import MarketplaceCard from '@/components/marketplace/MarketplaceCard.vue'
import type { MarketplaceItemType, MarketplaceTogglePayload } from '@/stores/marketplace'
import { useMarketplaceStore } from '@/stores/marketplace'
import { storeToRefs } from 'pinia'

const store = useMarketplaceStore()
const { items, loading, installing } = storeToRefs(store)

const keyword = ref('')
const filterType = ref<MarketplaceItemType | null>(null)
const filterEnabled = ref<boolean | null>(null)
const registerDialogVisible = ref(false)
const registering = ref(false)
const registerFormRef = ref()
const registerForm = reactive({ name: '', access_url: '', access_token: '', description: '' })
const registerRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  access_url: [{ required: true, message: '请输入访问地址', trigger: 'blur' }],
}

async function fetchData() {
  await store.fetchItems({
    item_type: filterType.value || undefined,
    enabled: filterEnabled.value ?? undefined,
    keyword: keyword.value || undefined,
  })
}

async function handleToggle(payload: MarketplaceTogglePayload) {
  if (payload.enabled) {
    await store.installItem(payload.item_type, payload.id)
    return
  }
  await store.uninstallItem(payload.item_type, payload.id)
}

async function handleRegister() {
  await registerFormRef.value.validate()
  registering.value = true
  try {
    await store.registerAgent({ ...registerForm })
    await fetchData()
    registerDialogVisible.value = false
    Object.assign(registerForm, { name: '', access_url: '', access_token: '', description: '' })
  } finally {
    registering.value = false
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
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
</style>
