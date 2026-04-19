import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MCPView from '../MCPView.vue'

vi.mock('@/api/index', () => ({
  marketplaceApi: {
    list: vi.fn().mockResolvedValue({ items: [] }),
    install: vi.fn().mockResolvedValue({ id: 1, enabled: true }),
    uninstall: vi.fn().mockResolvedValue({ id: 1, enabled: false }),
    registerAgent: vi.fn().mockResolvedValue({ id: 1 }),
  },
}))

describe('MCPView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('mounts without errors', () => {
    const wrapper = mount(MCPView, {
      global: { plugins: [createPinia()] }
    })
    expect(wrapper.exists()).toBe(true)
  })
})
