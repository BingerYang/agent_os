import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentApi, toolApi, skillApi, pipelineApi, detectionRuleApi } from '@/api/index'

export interface Tool {
  id: number
  name: string
  display_name: string
  description?: string
  protocol: string
  endpoint_url?: string
  enabled: boolean
  tags?: string[]
}

export interface Skill {
  id: number
  name: string
  description?: string
  tool_ids: number[]
  enabled: boolean
}

export interface Agent {
  id: number
  name: string
  description?: string
  agent_type: 'SINGLE' | 'SUB' | 'ORCHESTRATOR'
  llm_model_id?: number
  system_prompt?: string
  tool_ids: number[]
  skill_ids: number[]
  enabled: boolean
}

export interface DetectionRule {
  id: number
  name: string
  stage: 'PRE' | 'POST'
  rule_type: 'keyword' | 'llm_judge'
  rule_content: object
  reject_message?: string
  priority: number
  enabled: boolean
}

export interface Pipeline {
  id: number
  name: string
  pipeline_type: 'SINGLE_AGENT' | 'MULTI_AGENT'
  primary_agent_id?: number
  detection_rule_ids: number[]
  enabled: boolean
  timeout_seconds: number
  stream_output: boolean
}

export const useAgentStore = defineStore('agent', () => {
  const tools = ref<Tool[]>([])
  const skills = ref<Skill[]>([])
  const agents = ref<Agent[]>([])
  const pipelines = ref<Pipeline[]>([])
  const detectionRules = ref<DetectionRule[]>([])

  const loading = ref(false)

  // Tools
  async function fetchTools(params?: object) {
    const data: any = await toolApi.list(params)
    tools.value = data.items || []
    return data
  }
  async function createTool(payload: object) {
    const item = await toolApi.create(payload) as Tool
    tools.value.push(item)
    return item
  }
  async function updateTool(id: number, payload: object) {
    const item = await toolApi.update(id, payload) as Tool
    const idx = tools.value.findIndex(t => t.id === id)
    if (idx !== -1) tools.value[idx] = item
    return item
  }
  async function deleteTool(id: number) {
    await toolApi.delete(id)
    tools.value = tools.value.filter(t => t.id !== id)
  }
  async function toggleTool(id: number, enabled: boolean) {
    const item = await toolApi.toggle(id, enabled) as Tool
    const idx = tools.value.findIndex(t => t.id === id)
    if (idx !== -1) tools.value[idx] = item
    return item
  }

  // Agents
  async function fetchAgents(params?: object) {
    const data: any = await agentApi.list(params)
    agents.value = data.items || []
    return data
  }
  async function createAgent(payload: object) {
    const item = await agentApi.create(payload) as Agent
    agents.value.push(item)
    return item
  }
  async function updateAgent(id: number, payload: object) {
    const item = await agentApi.update(id, payload) as Agent
    const idx = agents.value.findIndex(a => a.id === id)
    if (idx !== -1) agents.value[idx] = item
    return item
  }
  async function deleteAgent(id: number) {
    await agentApi.delete(id)
    agents.value = agents.value.filter(a => a.id !== id)
  }
  async function toggleAgent(id: number, enabled: boolean) {
    const item = await agentApi.toggle(id, enabled) as Agent
    const idx = agents.value.findIndex(a => a.id === id)
    if (idx !== -1) agents.value[idx] = item
    return item
  }

  // Skills
  async function fetchSkills(params?: object) {
    const data: any = await skillApi.list(params)
    skills.value = data.items || []
    return data
  }
  async function createSkill(payload: object) {
    const item = await skillApi.create(payload) as Skill
    skills.value.push(item)
    return item
  }
  async function updateSkill(id: number, payload: object) {
    const item = await skillApi.update(id, payload) as Skill
    const idx = skills.value.findIndex(s => s.id === id)
    if (idx !== -1) skills.value[idx] = item
    return item
  }
  async function deleteSkill(id: number) {
    await skillApi.delete(id)
    skills.value = skills.value.filter(s => s.id !== id)
  }

  // Pipelines
  async function fetchPipelines(params?: object) {
    const data: any = await pipelineApi.list(params)
    pipelines.value = data.items || []
    return data
  }
  async function createPipeline(payload: object) {
    const item = await pipelineApi.create(payload) as Pipeline
    pipelines.value.push(item)
    return item
  }
  async function updatePipeline(id: number, payload: object) {
    const item = await pipelineApi.update(id, payload) as Pipeline
    const idx = pipelines.value.findIndex(p => p.id === id)
    if (idx !== -1) pipelines.value[idx] = item
    return item
  }
  async function deletePipeline(id: number) {
    await pipelineApi.delete(id)
    pipelines.value = pipelines.value.filter(p => p.id !== id)
  }

  // DetectionRules
  async function fetchDetectionRules(params?: object) {
    const data: any = await detectionRuleApi.list(params)
    detectionRules.value = data.items || []
    return data
  }
  async function createDetectionRule(payload: object) {
    const item = await detectionRuleApi.create(payload) as DetectionRule
    detectionRules.value.push(item)
    return item
  }
  async function updateDetectionRule(id: number, payload: object) {
    const item = await detectionRuleApi.update(id, payload) as DetectionRule
    const idx = detectionRules.value.findIndex(r => r.id === id)
    if (idx !== -1) detectionRules.value[idx] = item
    return item
  }
  async function deleteDetectionRule(id: number) {
    await detectionRuleApi.delete(id)
    detectionRules.value = detectionRules.value.filter(r => r.id !== id)
  }
  async function toggleDetectionRule(id: number, enabled: boolean) {
    const item = await detectionRuleApi.toggle(id, enabled) as DetectionRule
    const idx = detectionRules.value.findIndex(r => r.id === id)
    if (idx !== -1) detectionRules.value[idx] = item
    return item
  }

  return {
    tools, skills, agents, pipelines, detectionRules, loading,
    fetchTools, createTool, updateTool, deleteTool, toggleTool,
    fetchAgents, createAgent, updateAgent, deleteAgent, toggleAgent,
    fetchSkills, createSkill, updateSkill, deleteSkill,
    fetchPipelines, createPipeline, updatePipeline, deletePipeline,
    fetchDetectionRules, createDetectionRule, updateDetectionRule, deleteDetectionRule, toggleDetectionRule,
  }
})
