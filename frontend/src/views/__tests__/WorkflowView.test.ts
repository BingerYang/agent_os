import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WorkflowView from '../WorkflowView.vue'

// Mock API module
vi.mock('@/api/index', () => ({
  queryApi: {
    submit: vi.fn().mockResolvedValue({
      answer: '北京今天天气晴，18-26°C',
      pipeline_type: 'SINGLE_AGENT',
      tools_called: ['weather_query'],
      session_id: 'sess_test_001',
      latency_ms: 520,
    }),
  },
  pipelineApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        { id: 1, name: '测试流水线', pipeline_type: 'SINGLE_AGENT', enabled: true },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    }),
  },
}))

describe('WorkflowView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应正确挂载组件并显示三栏布局', () => {
    const wrapper = mount(WorkflowView, {
      global: {
        plugins: [createPinia()],
      },
    })
    expect(wrapper.exists()).toBe(true)
    // 三栏布局：左栏配置、中栏聊天、右栏检测规则
    expect(wrapper.find('.workflow-left').exists()).toBe(true)
    expect(wrapper.find('.workflow-center').exists()).toBe(true)
    expect(wrapper.find('.workflow-right').exists()).toBe(true)
  })

  it('应显示 Pipeline 选择器', () => {
    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })
    const selector = wrapper.find('[data-test="pipeline-selector"]')
    expect(selector.exists()).toBe(true)
  })

  it('应显示消息输入框和发送按钮', () => {
    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })
    const input = wrapper.find('[data-test="message-input"]')
    const sendBtn = wrapper.find('[data-test="send-button"]')
    expect(input.exists()).toBe(true)
    expect(sendBtn.exists()).toBe(true)
  })

  it('发送消息后应显示用户消息气泡', async () => {
    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })
    const input = wrapper.find('[data-test="message-input"]')
    await input.setValue('今天北京天气怎样？')
    await wrapper.find('[data-test="send-button"]').trigger('click')
    await wrapper.vm.$nextTick()

    const messages = wrapper.findAll('.message-bubble')
    const userMessages = messages.filter(m => m.classes('message-user'))
    expect(userMessages.length).toBeGreaterThan(0)
    expect(userMessages[0].text()).toContain('今天北京天气怎样？')
  })

  it('发送消息后应调用 queryApi.submit', async () => {
    const { queryApi } = await import('@/api/index')
    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })

    // 先选择一个 pipeline
    await wrapper.vm.$nextTick()

    const input = wrapper.find('[data-test="message-input"]')
    await input.setValue('测试消息')
    await wrapper.find('[data-test="send-button"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(queryApi.submit).toHaveBeenCalledWith(
      expect.objectContaining({
        query: '测试消息',
      })
    )
  })

  it('收到响应后应显示 Agent 回复气泡', async () => {
    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })
    await wrapper.vm.$nextTick()

    const input = wrapper.find('[data-test="message-input"]')
    await input.setValue('北京天气')
    await wrapper.find('[data-test="send-button"]').trigger('click')
    // 等待异步响应
    await new Promise(r => setTimeout(r, 100))
    await wrapper.vm.$nextTick()

    const agentMessages = wrapper.findAll('.message-bubble.message-agent')
    expect(agentMessages.length).toBeGreaterThan(0)
  })

  it('输入框为空时不应发送消息', async () => {
    const { queryApi } = await import('@/api/index')
    vi.mocked(queryApi.submit).mockClear()

    const wrapper = mount(WorkflowView, {
      global: { plugins: [createPinia()] },
    })
    await wrapper.find('[data-test="send-button"]').trigger('click')
    expect(queryApi.submit).not.toHaveBeenCalled()
  })
})
