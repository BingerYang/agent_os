<template>
  <div class="workflow-layout">
    <!-- 左栏：Pipeline 配置 + 模型参数 -->
    <div class="workflow-left">
      <div class="panel-header">
        <span class="panel-title">流水线配置</span>
      </div>

      <div class="panel-section">
        <div class="field-label">选择流水线</div>
        <el-select
          data-test="pipeline-selector"
          v-model="selectedPipelineId"
          placeholder="请选择流水线"
          style="width: 100%"
          @change="onPipelineChange"
        >
          <el-option
            v-for="p in pipelines"
            :key="p.id"
            :label="p.name"
            :value="p.id"
          >
            <span>{{ p.name }}</span>
            <el-tag size="small" style="float: right; margin-top: 4px" :type="p.pipeline_type === 'SINGLE_AGENT' ? '' : 'warning'">
              {{ p.pipeline_type === 'SINGLE_AGENT' ? '单 Agent' : '多 Agent' }}
            </el-tag>
          </el-option>
        </el-select>
      </div>

      <div v-if="currentPipeline" class="panel-section">
        <div class="field-label">流水线参数</div>
        <el-descriptions :column="1" size="small" border>
          <el-descriptions-item label="类型">
            <el-tag size="small">{{ currentPipeline.pipeline_type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="超时（秒）">
            {{ currentPipeline.timeout_seconds }}
          </el-descriptions-item>
          <el-descriptions-item label="流式输出">
            <el-switch v-model="streamMode" size="small" />
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-if="!selectedPipelineId" class="empty-hint">
        请先选择一条流水线
      </div>
    </div>

    <!-- 中栏：聊天沙盒 -->
    <div class="workflow-center">
      <div class="panel-header" style="padding: 12px 16px; border-bottom: 1px solid #ebeef5;">
        <span class="panel-title">对话沙盒</span>
        <el-button size="small" text @click="clearMessages">清空对话</el-button>
      </div>

      <div class="chat-area" ref="chatAreaRef">
        <div v-if="messages.length === 0" class="chat-empty">
          <p>在下方输入问题，开始与 Agent 对话</p>
        </div>
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-bubble"
          :class="msg.role === 'user' ? 'message-user' : 'message-agent'"
        >
          <div class="bubble-content">{{ msg.content }}</div>
          <div v-if="msg.tools_called?.length" class="bubble-tools">
            <el-tag v-for="t in msg.tools_called" :key="t" size="small" type="info" style="margin-right: 4px">{{ t }}</el-tag>
          </div>
          <div class="bubble-meta">{{ msg.time }}</div>
        </div>
        <div v-if="querying" class="message-bubble message-agent loading-bubble">
          <div class="bubble-content"><span class="dot-flash">●●●</span></div>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          data-test="message-input"
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行..."
          resize="none"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          data-test="send-button"
          type="primary"
          :loading="querying"
          :disabled="!selectedPipelineId"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>

    <!-- 右栏：检测规则预览 -->
    <div class="workflow-right">
      <div class="panel-header">
        <span class="panel-title">检测规则</span>
      </div>

      <div v-if="!selectedPipelineId" class="empty-hint">
        选择流水线后显示检测规则
      </div>

      <div v-else>
        <div class="rule-section">
          <div class="rule-stage-label">前置检测（PRE）</div>
          <div v-if="preRules.length === 0" class="rule-empty">无前置规则</div>
          <div v-for="rule in preRules" :key="rule.id" class="rule-item">
            <div class="rule-name">{{ rule.name }}</div>
            <div class="rule-meta">
              <el-tag size="small" :type="rule.rule_type === 'keyword' ? '' : 'warning'">{{ rule.rule_type }}</el-tag>
              <StatusTag :enabled="rule.enabled" />
            </div>
          </div>
        </div>

        <el-divider />

        <div class="rule-section">
          <div class="rule-stage-label">后置检测（POST）</div>
          <div v-if="postRules.length === 0" class="rule-empty">无后置规则</div>
          <div v-for="rule in postRules" :key="rule.id" class="rule-item">
            <div class="rule-name">{{ rule.name }}</div>
            <div class="rule-meta">
              <el-tag size="small" :type="rule.rule_type === 'keyword' ? '' : 'warning'">{{ rule.rule_type }}</el-tag>
              <StatusTag :enabled="rule.enabled" />
            </div>
          </div>
        </div>
      </div>

      <div v-if="lastResult" class="result-panel">
        <el-divider />
        <div class="field-label">最近调用信息</div>
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="会话 ID">{{ lastResult.session_id }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ lastResult.latency_ms }} ms</el-descriptions-item>
          <el-descriptions-item label="工具调用">{{ lastResult.tools_called?.join(', ') || '无' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import StatusTag from '@/components/common/StatusTag.vue'
import { pipelineApi, queryApi } from '@/api/index'

interface Message {
  role: 'user' | 'agent'
  content: string
  time: string
  tools_called?: string[]
}

const pipelines = ref<any[]>([])
const selectedPipelineId = ref<number | null>(null)
const streamMode = ref(false)
const messages = ref<Message[]>([])
const inputText = ref('')
const querying = ref(false)
const lastResult = ref<any>(null)
const chatAreaRef = ref<HTMLElement>()

const currentPipeline = computed(() => pipelines.value.find(p => p.id === selectedPipelineId.value) || null)

const preRules = computed(() => {
  if (!currentPipeline.value?.detection_rules) return []
  return currentPipeline.value.detection_rules.filter((r: any) => r.stage === 'PRE')
})
const postRules = computed(() => {
  if (!currentPipeline.value?.detection_rules) return []
  return currentPipeline.value.detection_rules.filter((r: any) => r.stage === 'POST')
})

async function fetchPipelines() {
  try {
    const data: any = await pipelineApi.list({ page_size: 100 })
    pipelines.value = data.items || []
  } catch {
    // ignore on initial load
  }
}

async function onPipelineChange(id: number) {
  try {
    const detail: any = await pipelineApi.get(id)
    const idx = pipelines.value.findIndex(p => p.id === id)
    if (idx !== -1) pipelines.value[idx] = detail
  } catch {
    // ignore
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  if (!selectedPipelineId.value) {
    ElMessage.warning('请先选择流水线')
    return
  }

  const now = new Date().toLocaleTimeString()
  messages.value.push({ role: 'user', content: text, time: now })
  inputText.value = ''
  querying.value = true
  await nextTick()
  scrollToBottom()

  try {
    const result: any = await queryApi.submit({
      query: text,
      pipeline_id: selectedPipelineId.value,
      stream: streamMode.value,
    })
    lastResult.value = result
    messages.value.push({
      role: 'agent',
      content: result.answer,
      time: new Date().toLocaleTimeString(),
      tools_called: result.tools_called,
    })
  } catch (e: any) {
    const errMsg = e?.message || '查询失败'
    messages.value.push({ role: 'agent', content: `[错误] ${errMsg}`, time: new Date().toLocaleTimeString() })
  } finally {
    querying.value = false
    await nextTick()
    scrollToBottom()
  }
}

function clearMessages() {
  messages.value = []
  lastResult.value = null
}

function scrollToBottom() {
  if (chatAreaRef.value) {
    chatAreaRef.value.scrollTop = chatAreaRef.value.scrollHeight
  }
}

onMounted(fetchPipelines)
</script>

<style scoped>
.workflow-layout {
  display: flex;
  height: calc(100vh - 60px);
  overflow: hidden;
}

.workflow-left,
.workflow-right {
  width: 280px;
  flex-shrink: 0;
  overflow-y: auto;
  padding: 16px;
  border-right: 1px solid #ebeef5;
  background: #fafafa;
}

.workflow-right {
  border-right: none;
  border-left: 1px solid #ebeef5;
}

.workflow-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.panel-section {
  margin-bottom: 16px;
}

.field-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.empty-hint {
  color: #c0c4cc;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fff;
}

.chat-empty {
  color: #c0c4cc;
  text-align: center;
  padding: 40px 0;
  font-size: 14px;
}

.message-bubble {
  margin-bottom: 16px;
  max-width: 75%;
}

.message-user {
  margin-left: auto;
}

.message-agent {
  margin-right: auto;
}

.bubble-content {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.message-user .bubble-content {
  background: #409eff;
  color: #fff;
  border-radius: 10px 2px 10px 10px;
}

.message-agent .bubble-content {
  background: #f0f2f5;
  color: #303133;
  border-radius: 2px 10px 10px 10px;
}

.bubble-tools { margin-top: 4px; }

.bubble-meta {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 4px;
  padding: 0 2px;
}

.message-user .bubble-meta { text-align: right; }

.dot-flash { color: #909399; letter-spacing: 4px; }

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fff;
  align-items: flex-end;
}

.chat-input-area .el-textarea { flex: 1; }
.chat-input-area .el-button { flex-shrink: 0; height: 72px; width: 80px; }

.rule-section { margin-bottom: 4px; }
.rule-stage-label { font-size: 12px; font-weight: 600; color: #606266; margin-bottom: 8px; }
.rule-empty { font-size: 12px; color: #c0c4cc; padding: 4px 0; }
.rule-item {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
}
.rule-name { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.rule-meta { display: flex; gap: 6px; align-items: center; }

.result-panel { font-size: 13px; }
</style>
