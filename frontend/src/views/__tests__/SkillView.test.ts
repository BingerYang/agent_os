import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SkillView from '../SkillView.vue'

vi.mock('@/api/index', () => ({
  skillApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
  toolApi: {
    list: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

describe('SkillView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('mounts without errors', () => {
    const wrapper = mount(SkillView, {
      global: { plugins: [createPinia()] }
    })
    expect(wrapper.exists()).toBe(true)
  })
})
