import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PipelineView from '../PipelineView.vue'

vi.mock('@/api/index', () => ({
  detectionRuleApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}))

describe('PipelineView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('mounts without errors', () => {
    const wrapper = mount(PipelineView, {
      global: { plugins: [createPinia()] }
    })
    expect(wrapper.exists()).toBe(true)
  })
})
