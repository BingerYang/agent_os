import { ElMessage } from 'element-plus'
import { createRouter, createWebHistory } from 'vue-router'
import http from '@/api'

interface ModelConfigListResponse {
  items?: unknown[]
  total?: number
}

async function hasConfiguredModels() {
  try {
    const data = await http.get('/models-config') as ModelConfigListResponse | unknown[]
    if (Array.isArray(data)) {
      return data.length > 0
    }
    if (Array.isArray(data?.items)) {
      return data.items.length > 0
    }
    return (data?.total || 0) > 0
  } catch {
    return true
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/workflow',
      meta: { title: '首页' }
    },
    {
      path: '/workflow',
      name: 'workflow',
      component: () => import('@/views/WorkflowView.vue'),
      meta: { title: 'Agent 工作流' }
    },
    {
      path: '/mcp',
      name: 'mcp',
      component: () => import('@/views/MCPView.vue'),
      meta: { title: '插件广场' }
    },
    {
      path: '/skills',
      name: 'skills',
      component: () => import('@/views/SkillView.vue'),
      meta: { title: 'Skill 管理' }
    },
    {
      path: '/pipelines',
      name: 'pipelines',
      component: () => import('@/views/PipelineView.vue'),
      meta: { title: '检测规则管理' }
    },
    {
      path: '/models',
      name: 'models',
      component: () => import('@/views/ModelView.vue'),
      meta: { title: '模型配置' }
    },
    {
      path: '/agents',
      name: 'agents',
      component: () => import('@/views/AgentView.vue'),
      meta: { title: 'Agent 管理' }
    }
  ]
})

router.beforeEach(async (to) => {
  if (to.name === 'models') {
    return true
  }

  const configured = await hasConfiguredModels()
  if (!configured) {
    ElMessage.warning('请先在模型配置页面添加 LLM 模型')
  }

  return true
})

export default router
