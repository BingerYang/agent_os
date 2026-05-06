import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Pagination,
  Popconfirm,
  Select,
  Slider,
  Spin,
  Switch,
  Tabs,
  message,
} from 'antd'
import type { TabsProps } from 'antd'
import StatusTag from '../components/StatusTag'
import {
  agentApi,
  detectionRuleApi,
  mcpServerApi,
  modelApi,
  normalizeDetailResponse,
  normalizeListResponse,
  skillApi,
  toolApi,
} from '../api'

type AgentType = 'SINGLE' | 'SUB' | 'ORCHESTRATOR'
type PlatformType = 'local' | 'openai' | 'third-party'
type PublishStatus = 'published' | 'draft'
type RouteStrategy = 'smart' | 'intent_rule'
type EnabledFilter = 'enabled' | 'disabled'
type RuleStage = 'PRE' | 'POST'

interface RoutingIntentRule {
  key?: string
  sub_agent_ids?: number[]
  [key: string]: unknown
}

interface IntentEntityRule {
  stage?: RuleStage
  rule_ids?: number[]
  [key: string]: unknown
}

interface AgentListItem {
  id: number
  name: string
  agent_type: AgentType
  status: PublishStatus
  enabled: boolean
  description?: string
  tool_ids?: number[]
  skill_ids?: number[]
  llm_model_id?: number
  source_platform?: string
  pipeline_uid?: string
  sub_agent_ids?: number[]
}

interface AgentDetail extends AgentListItem {
  access_url?: string
  access_token?: string
  system_prompt?: string
  temperature?: number
  max_tokens?: number
  intent_recognition_enabled?: boolean
  intent_model_id?: number
  intent_confidence_threshold?: number
  intent_system_prompt?: string
  routing_strategy?: RouteStrategy
  routing_model_id?: number
  routing_threshold?: number
  routing_system_prompt?: string
  routing_intent_rules?: RoutingIntentRule[]
  intent_entity_schema?: IntentEntityRule[]
}

interface AgentFormValues {
  name: string
  agent_type: AgentType
  source_platform: PlatformType
  access_url?: string
  access_token?: string
  description?: string
  llm_model_id?: number
  system_prompt?: string
  temperature: number
  max_tokens?: number
  intent_recognition_enabled: boolean
  intent_model_id?: number
  intent_confidence_threshold: number
  intent_system_prompt?: string
  mcp_server_filter_id?: number
  tool_ids: number[]
  skill_ids: number[]
  routing_strategy: RouteStrategy
  routing_model_id?: number
  routing_threshold: number
  routing_system_prompt?: string
  sub_agent_ids: number[]
  pre_rule_ids_text?: string
  post_rule_ids_text?: string
  enabled: boolean
}

interface ModelOption {
  id: number
  name: string
  supplier?: string
}

interface ToolOption {
  id: number
  name: string
  display_name?: string
  description?: string
  protocol: 'MCP' | 'HTTP' | 'BUILTIN'
  mcp_server_id?: number | null
}

interface SkillOption {
  id: number
  name: string
  description?: string
  category?: string
}

interface MCPServerOption {
  id: number
  name: string
  display_name?: string
}

interface DetectionRuleOption {
  id: number
  name: string
  stage: RuleStage
}

interface PublishAgentResponse {
  pipeline_uid?: string
}

const defaultFormValues: AgentFormValues = {
  name: '',
  agent_type: 'SINGLE',
  source_platform: 'local',
  access_url: '',
  access_token: '',
  description: '',
  llm_model_id: undefined,
  system_prompt: '',
  temperature: 0.7,
  max_tokens: 2048,
  intent_recognition_enabled: false,
  intent_model_id: undefined,
  intent_confidence_threshold: 0.85,
  intent_system_prompt: '',
  mcp_server_filter_id: undefined,
  tool_ids: [],
  skill_ids: [],
  routing_strategy: 'smart',
  routing_model_id: undefined,
  routing_threshold: 0.8,
  routing_system_prompt: '',
  sub_agent_ids: [],
  pre_rule_ids_text: '',
  post_rule_ids_text: '',
  enabled: true,
}

const agentTypeTagClass: Record<AgentType, string> = {
  SINGLE: 'tag-blue',
  SUB: 'tag-orange',
  ORCHESTRATOR: 'tag-red',
}

const publishStatusTagClass: Record<PublishStatus, string> = {
  published: 'tag-green',
  draft: 'tag-gray',
}

const protocolTagClass: Record<ToolOption['protocol'], string> = {
  MCP: 'tag-blue',
  HTTP: 'tag-green',
  BUILTIN: 'tag-purple',
}

const ruleStageLabel: Record<RuleStage, string> = {
  PRE: '前置',
  POST: '后置',
}

const parseIdLines = (value?: string) =>
  (value || '')
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))

const ruleLinesToText = (ids: number[]) => ids.join('\n')

const pickRuleIdsFromSchema = (schema: AgentDetail['intent_entity_schema'], stage: RuleStage) => {
  if (!Array.isArray(schema)) return []
  return schema
    .filter((item) => item?.stage === stage && Array.isArray(item.rule_ids))
    .flatMap((item) => item.rule_ids || [])
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id))
}

const toFormValues = (detail?: Partial<AgentDetail>): AgentFormValues => ({
  ...defaultFormValues,
  ...detail,
  source_platform: detail?.source_platform === 'openai' || detail?.source_platform === 'third-party' ? detail.source_platform : 'local',
  temperature: typeof detail?.temperature === 'number' ? detail.temperature : 0.7,
  max_tokens: typeof detail?.max_tokens === 'number' ? detail.max_tokens : 2048,
  intent_recognition_enabled: Boolean(detail?.intent_recognition_enabled),
  intent_confidence_threshold:
    typeof detail?.intent_confidence_threshold === 'number' ? detail.intent_confidence_threshold : 0.85,
  routing_strategy: detail?.routing_strategy || 'smart',
  routing_threshold: typeof detail?.routing_threshold === 'number' ? detail.routing_threshold : 0.8,
  tool_ids: detail?.tool_ids || [],
  skill_ids: detail?.skill_ids || [],
  sub_agent_ids: detail?.sub_agent_ids || [],
  pre_rule_ids_text: ruleLinesToText(pickRuleIdsFromSchema(detail?.intent_entity_schema, 'PRE')),
  post_rule_ids_text: ruleLinesToText(pickRuleIdsFromSchema(detail?.intent_entity_schema, 'POST')),
})

const buildSubmitPayload = (values: AgentFormValues, currentAgent?: AgentDetail | null) => {
  const isOrchestrator = values.agent_type === 'ORCHESTRATOR'
  const preRuleIds = parseIdLines(values.pre_rule_ids_text)
  const postRuleIds = parseIdLines(values.post_rule_ids_text)

  return {
    name: values.name.trim(),
    agent_type: values.agent_type,
    source_platform: values.source_platform,
    access_url: values.source_platform === 'local' ? '' : values.access_url?.trim() || '',
    access_token: values.source_platform === 'local' ? '' : values.access_token?.trim() || '',
    description: values.description?.trim() || '',
    llm_model_id: values.llm_model_id,
    system_prompt: values.system_prompt?.trim() || '',
    status: currentAgent?.status || 'draft',
    temperature: values.temperature,
    max_tokens: values.max_tokens,
    intent_recognition_enabled: !isOrchestrator && values.intent_recognition_enabled,
    intent_model_id: !isOrchestrator ? values.intent_model_id : undefined,
    intent_confidence_threshold: !isOrchestrator ? values.intent_confidence_threshold : undefined,
    intent_system_prompt: !isOrchestrator ? values.intent_system_prompt?.trim() || '' : '',
    intent_entity_schema: [
      { stage: 'PRE', rule_ids: preRuleIds },
      { stage: 'POST', rule_ids: postRuleIds },
    ],
    routing_strategy: isOrchestrator ? values.routing_strategy : 'smart',
    routing_model_id: isOrchestrator ? values.routing_model_id : undefined,
    routing_threshold: isOrchestrator ? values.routing_threshold : 0.8,
    routing_system_prompt: isOrchestrator ? values.routing_system_prompt?.trim() || '' : '',
    sub_agent_ids: isOrchestrator ? values.sub_agent_ids : [],
    tool_ids: !isOrchestrator ? values.tool_ids : [],
    skill_ids: !isOrchestrator ? values.skill_ids : [],
    enabled: values.enabled,
  }
}

const getModelLabel = (modelId: number | undefined, models: ModelOption[]) => {
  const model = models.find((item) => item.id === modelId)
  if (!model) return '未绑定'
  return model.supplier ? `${model.name} / ${model.supplier}` : model.name
}

const getPlatformLabel = (platform?: string) => {
  if (platform === 'openai') return 'OpenAI'
  if (platform === 'third-party') return '第三方'
  return '本地'
}

export default function AgentPage() {
  const [form] = Form.useForm<AgentFormValues>()
  const [agents, setAgents] = useState<AgentListItem[]>([])
  const [models, setModels] = useState<ModelOption[]>([])
  const [tools, setTools] = useState<ToolOption[]>([])
  const [skills, setSkills] = useState<SkillOption[]>([])
  const [servers, setServers] = useState<MCPServerOption[]>([])
  const [rules, setRules] = useState<DetectionRuleOption[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [metaLoading, setMetaLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [typeFilter, setTypeFilter] = useState<AgentType | undefined>(undefined)
  const [enabledFilter, setEnabledFilter] = useState<EnabledFilter | undefined>(undefined)
  const [publishStatusFilter, setPublishStatusFilter] = useState<PublishStatus | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerMode, setDrawerMode] = useState<'create' | 'edit'>('create')
  const [editingAgent, setEditingAgent] = useState<AgentDetail | null>(null)
  const [activeTab, setActiveTab] = useState('basic')
  const pageSize = 20

  const currentAgentType = Form.useWatch('agent_type', form) || 'SINGLE'
  const currentPlatform = Form.useWatch('source_platform', form) || 'local'
  const currentServerFilter = Form.useWatch('mcp_server_filter_id', form)
  const selectedToolIds = Form.useWatch('tool_ids', form) || []
  const selectedSkillIds = Form.useWatch('skill_ids', form) || []
  const selectedSubAgentIds = Form.useWatch('sub_agent_ids', form) || []
  const preRuleIds = parseIdLines(Form.useWatch('pre_rule_ids_text', form))
  const postRuleIds = parseIdLines(Form.useWatch('post_rule_ids_text', form))

  const loadMeta = useCallback(async () => {
    setMetaLoading(true)
    try {
      const [modelResponse, toolResponse, skillResponse, serverResponse, ruleResponse] = await Promise.all([
        modelApi.list({ page: 1, page_size: 500 }),
        toolApi.list({ page: 1, page_size: 500 }),
        skillApi.list({ page: 1, page_size: 500 }),
        mcpServerApi.list({ page: 1, page_size: 200 }),
        detectionRuleApi.list({ page: 1, page_size: 500 }),
      ])
      setModels(normalizeListResponse<ModelOption>(modelResponse).items)
      setTools(normalizeListResponse<ToolOption>(toolResponse).items)
      setSkills(normalizeListResponse<SkillOption>(skillResponse).items)
      setServers(normalizeListResponse<MCPServerOption>(serverResponse).items)
      setRules(normalizeListResponse<DetectionRuleOption>(ruleResponse).items)
    } finally {
      setMetaLoading(false)
    }
  }, [])

  const loadAgents = useCallback(async () => {
    setListLoading(true)
    try {
      const response = await agentApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
        agent_type: typeFilter,
        enabled: enabledFilter === undefined ? undefined : enabledFilter === 'enabled',
        status: publishStatusFilter,
      })
      const result = normalizeListResponse<AgentListItem>(response)
      setAgents(
        result.items.map((item) => ({
          ...item,
          status: item.status || 'draft',
        })),
      )
      setTotal(result.total)
    } finally {
      setListLoading(false)
    }
  }, [enabledFilter, keyword, page, publishStatusFilter, typeFilter])

  const loadAgentDetail = useCallback(
    async (id: number) => {
      setDetailLoading(true)
      try {
        const detail = normalizeDetailResponse<AgentDetail>(await agentApi.get(id))
        const summary = agents.find((item) => item.id === id)
        const normalizedDetail: AgentDetail = {
          ...summary,
          ...detail,
          status: detail.status || 'draft',
          sub_agent_ids: detail.sub_agent_ids || summary?.sub_agent_ids || [],
        }
        setEditingAgent(normalizedDetail)
        form.setFieldsValue(toFormValues(normalizedDetail))
      } finally {
        setDetailLoading(false)
      }
    },
    [agents, form],
  )

  useEffect(() => {
    void Promise.all([loadAgents(), loadMeta()])
  }, [loadAgents, loadMeta])

  useEffect(() => {
    if (currentAgentType === 'ORCHESTRATOR' && ['intent', 'tools', 'skills'].includes(activeTab)) {
      setActiveTab('basic')
    }
  }, [activeTab, currentAgentType])

  const filteredToolOptions = useMemo(() => {
    if (!currentServerFilter) return tools
    return tools.filter((item) => item.mcp_server_id === currentServerFilter)
  }, [currentServerFilter, tools])

  const childAgentOptions = useMemo(
    () =>
      agents.filter((item) => item.agent_type !== 'ORCHESTRATOR' && item.id !== editingAgent?.id),
    [agents, editingAgent?.id],
  )

  const selectedTools = useMemo(
    () => tools.filter((item) => selectedToolIds.includes(item.id)),
    [selectedToolIds, tools],
  )

  const selectedSkills = useMemo(
    () => skills.filter((item) => selectedSkillIds.includes(item.id)),
    [selectedSkillIds, skills],
  )

  const selectedSubAgents = useMemo(
    () => childAgentOptions.filter((item) => selectedSubAgentIds.includes(item.id)),
    [childAgentOptions, selectedSubAgentIds],
  )

  const openCreateDrawer = () => {
    setDrawerMode('create')
    setEditingAgent(null)
    setActiveTab('basic')
    form.resetFields()
    form.setFieldsValue(defaultFormValues)
    setDrawerOpen(true)
  }

  const openEditDrawer = async (id: number) => {
    setDrawerMode('edit')
    setActiveTab('basic')
    setDrawerOpen(true)
    form.resetFields()
    form.setFieldsValue(defaultFormValues)
    await loadAgentDetail(id)
  }

  const closeDrawer = () => {
    setDrawerOpen(false)
    setDetailLoading(false)
    setEditingAgent(null)
    setActiveTab('basic')
    form.resetFields()
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    const payload = buildSubmitPayload(values, editingAgent)
    setSaveLoading(true)
    try {
      if (drawerMode === 'create') {
        await agentApi.create(payload)
      } else if (editingAgent) {
        await agentApi.update(editingAgent.id, payload)
      }
      message.success('保存成功')
      closeDrawer()
      await loadAgents()
    } finally {
      setSaveLoading(false)
    }
  }

  const handlePublish = async (agent: AgentListItem) => {
    const newStatus: PublishStatus = agent.status === 'published' ? 'draft' : 'published'
    const response = await agentApi.publish(agent.id, newStatus, agent.sub_agent_ids || [])
    const result = normalizeDetailResponse<PublishAgentResponse>(response)
    setAgents((prev) =>
      prev.map((item) =>
        item.id === agent.id
          ? { ...item, status: newStatus, pipeline_uid: result.pipeline_uid ?? item.pipeline_uid }
          : item,
      ),
    )
    if (editingAgent?.id === agent.id) {
      setEditingAgent((prev) =>
        prev
          ? {
              ...prev,
              status: newStatus,
              pipeline_uid: result.pipeline_uid ?? prev.pipeline_uid,
            }
          : prev,
      )
    }
    message.success(newStatus === 'published' ? `已发布，Pipeline ID: ${result.pipeline_uid || '已生成'}` : '已下架')
  }

  const handleToggle = async (agent: AgentListItem) => {
    await agentApi.toggle(agent.id, !agent.enabled)
    setAgents((prev) => prev.map((item) => (item.id === agent.id ? { ...item, enabled: !item.enabled } : item)))
    if (editingAgent?.id === agent.id) {
      setEditingAgent((prev) => (prev ? { ...prev, enabled: !prev.enabled } : prev))
      form.setFieldValue('enabled', !agent.enabled)
    }
    message.success(!agent.enabled ? '已启用' : '已禁用')
  }

  const handleDelete = async (agent: AgentListItem) => {
    await agentApi.delete(agent.id)
    setAgents((prev) => prev.filter((item) => item.id !== agent.id))
    if (editingAgent?.id === agent.id) {
      closeDrawer()
    }
    message.success('删除成功')
    if (agents.length === 1 && page > 1) {
      setPage((prev) => prev - 1)
    } else {
      await loadAgents()
    }
  }

  const renderRulePreview = (ruleIds: number[], stage: RuleStage) => {
    const matchedRules = rules.filter((item) => item.stage === stage && ruleIds.includes(item.id))
    if (!matchedRules.length) {
      return <span className="chip">暂无{ruleStageLabel[stage]}规则</span>
    }
    return matchedRules.map((rule) => (
      <span key={rule.id} className="chip">
        #{rule.id} {rule.name}
      </span>
    ))
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'basic',
      label: '基础配置 🔧',
      children: (
        <div className="form-section">
          <div className="form-grid-2">
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
              <Input placeholder="请输入 Agent 名称" />
            </Form.Item>
            <Form.Item label="类型" name="agent_type" rules={[{ required: true, message: '请选择 Agent 类型' }]}>
              <Select
                options={[
                  { label: 'SINGLE', value: 'SINGLE' },
                  { label: 'SUB', value: 'SUB' },
                  { label: 'ORCHESTRATOR', value: 'ORCHESTRATOR' },
                ]}
              />
            </Form.Item>
          </div>
          <div className="form-grid-2">
            <Form.Item label="来源平台" name="source_platform" rules={[{ required: true, message: '请选择来源平台' }]}>
              <Select
                options={[
                  { label: '本地', value: 'local' },
                  { label: 'OpenAI', value: 'openai' },
                  { label: '第三方', value: 'third-party' },
                ]}
              />
            </Form.Item>
            <Form.Item label="启用状态" name="enabled" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </div>
          {currentPlatform !== 'local' ? (
            <div className="form-grid-2">
              <Form.Item label="访问地址" name="access_url" rules={[{ required: true, message: '请输入访问地址' }]}>
                <Input placeholder="请输入远程 Agent 访问地址" />
              </Form.Item>
              <Form.Item label="访问令牌" name="access_token">
                <Input.Password placeholder="请输入访问令牌" />
              </Form.Item>
            </div>
          ) : null}
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={4} placeholder="请输入 Agent 描述" />
          </Form.Item>
        </div>
      ),
    },
    {
      key: 'llm',
      label: 'LLM 模型 🧠',
      children: (
        <div className="form-section">
          <Form.Item label="绑定模型" name="llm_model_id">
            <Select
              allowClear
              placeholder="请选择模型"
              loading={metaLoading}
              options={models.map((item) => ({
                label: item.supplier ? `${item.name} / ${item.supplier}` : item.name,
                value: item.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="系统提示词" name="system_prompt">
            <Input.TextArea rows={7} className="mono-textarea" placeholder="请输入系统提示词" />
          </Form.Item>
          <div className="form-grid-2">
            <Form.Item label="Temperature" name="temperature">
              <Slider min={0} max={2} step={0.1} />
            </Form.Item>
            <Form.Item label="Max Tokens" name="max_tokens">
              <InputNumber min={256} max={32768} style={{ width: '100%' }} />
            </Form.Item>
          </div>
        </div>
      ),
    },
  ]

  if (currentAgentType !== 'ORCHESTRATOR') {
    tabItems.push(
      {
        key: 'intent',
        label: '意图识别 🎯',
        children: (
          <div className="form-section">
            <Form.Item label="启用开关" name="intent_recognition_enabled" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
            <div className="form-grid-2">
              <Form.Item label="识别 LLM" name="intent_model_id">
                <Select
                  allowClear
                  placeholder="请选择识别模型"
                  loading={metaLoading}
                  options={models.map((item) => ({
                    label: item.supplier ? `${item.name} / ${item.supplier}` : item.name,
                    value: item.id,
                  }))}
                />
              </Form.Item>
              <Form.Item label="置信度阈值" name="intent_confidence_threshold">
                <Slider min={0} max={1} step={0.01} />
              </Form.Item>
            </div>
            <Form.Item label="系统提示词" name="intent_system_prompt">
              <Input.TextArea rows={6} className="mono-textarea" placeholder="请输入意图识别系统提示词" />
            </Form.Item>
          </div>
        ),
      },
      {
        key: 'tools',
        label: '工具绑定 🔧',
        children: (
          <div className="form-section">
            <Form.Item label="MCP Server 筛选" name="mcp_server_filter_id">
              <Select
                allowClear
                placeholder="按 Server 筛选工具"
                loading={metaLoading}
                options={servers.map((item) => ({
                  label: item.display_name || item.name,
                  value: item.id,
                }))}
              />
            </Form.Item>
            <Form.Item label="工具多选" name="tool_ids">
              <Select
                mode="multiple"
                placeholder="请选择工具"
                loading={metaLoading}
                options={filteredToolOptions.map((item) => ({
                  label: `${item.display_name || item.name} (${item.protocol})`,
                  value: item.id,
                }))}
              />
            </Form.Item>
            <div className="form-section-title">已绑定工具</div>
            {selectedTools.length ? (
              selectedTools.map((item) => (
                <div key={item.id} className="mini-card">
                  <div className="mini-card-title">
                    <span>{item.display_name || item.name}</span>
                    <span className={`tag ${protocolTagClass[item.protocol]}`}>{item.protocol}</span>
                  </div>
                  <div className="mini-card-desc">{item.description || '暂无描述'}</div>
                </div>
              ))
            ) : (
              <div className="empty-state" style={{ padding: '24px 12px' }}>
                <div className="empty-state-text">尚未绑定工具</div>
              </div>
            )}
          </div>
        ),
      },
      {
        key: 'skills',
        label: '技能绑定 ⚡',
        children: (
          <div className="form-section">
            <Form.Item label="技能多选" name="skill_ids">
              <Select
                mode="multiple"
                placeholder="请选择技能"
                loading={metaLoading}
                options={skills.map((item) => ({
                  label: item.name,
                  value: item.id,
                }))}
              />
            </Form.Item>
            <div className="form-section-title">已选技能</div>
            {selectedSkills.length ? (
              selectedSkills.map((item) => (
                <div key={item.id} className="mini-card">
                  <div className="mini-card-title">
                    <span>{item.name}</span>
                    <span className="tag tag-blue">{item.category || 'skill'}</span>
                  </div>
                  <div className="mini-card-desc">{item.description || '暂无描述'}</div>
                </div>
              ))
            ) : (
              <div className="empty-state" style={{ padding: '24px 12px' }}>
                <div className="empty-state-text">尚未选择技能</div>
              </div>
            )}
          </div>
        ),
      },
    )
  } else {
    tabItems.push({
      key: 'orchestrator',
      label: '编排配置 🎛️',
      children: (
        <div className="form-section">
          <Form.Item label="路由 LLM" name="routing_model_id">
            <Select
              allowClear
              placeholder="请选择路由模型"
              loading={metaLoading}
              options={models.map((item) => ({
                label: item.supplier ? `${item.name} / ${item.supplier}` : item.name,
                value: item.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="置信阈值" name="routing_threshold">
            <Slider min={0} max={1} step={0.01} />
          </Form.Item>
        </div>
      ),
    })
    tabItems.push({
      key: 'sub_agents',
      label: '子 Agent 🤝',
      children: (
        <div className="form-section">
          <Form.Item label="子 Agent" name="sub_agent_ids">
            <Select
              mode="multiple"
              placeholder="请选择子 Agent（可多选）"
              options={childAgentOptions.map((item) => ({
                label: item.name,
                value: item.id,
              }))}
            />
          </Form.Item>
          <div className="form-section-title">已选子 Agent</div>
          {selectedSubAgents.length ? (
            selectedSubAgents.map((item) => (
              <div key={item.id} className="mini-card">
                <div className="mini-card-title">
                  <span>{item.name}</span>
                  <span className={`tag ${agentTypeTagClass[item.agent_type]}`}>{item.agent_type}</span>
                </div>
                <div className="mini-card-desc">{item.description || '暂无描述'}</div>
              </div>
            ))
          ) : (
            <div className="empty-state" style={{ padding: '24px 12px' }}>
              <div className="empty-state-text">尚未配置子 Agent</div>
            </div>
          )}
        </div>
      ),
    })
  }

  tabItems.push({
    key: 'rules',
    label: '检测规则 🛡️',
    children: (
      <div className="form-section">
        <div className="form-grid-2">
          <Form.Item label="前置检测链" name="pre_rule_ids_text">
            <Input.TextArea rows={7} className="mono-textarea" placeholder="每行输入一个规则 ID" />
          </Form.Item>
          <Form.Item label="后置检测链" name="post_rule_ids_text">
            <Input.TextArea rows={7} className="mono-textarea" placeholder="每行输入一个规则 ID" />
          </Form.Item>
        </div>
        <div className="form-grid-2">
          <div>
            <div className="form-section-title">前置规则预览</div>
            <div className="chip-list">{renderRulePreview(preRuleIds, 'PRE')}</div>
          </div>
          <div>
            <div className="form-section-title">后置规则预览</div>
            <div className="chip-list">{renderRulePreview(postRuleIds, 'POST')}</div>
          </div>
        </div>
        <div className="form-section-title">可用规则参考</div>
        {rules.length ? (
          rules.map((rule) => (
            <div key={rule.id} className="kv-row">
              <div className="kv-label">规则 #{rule.id}</div>
              <div className="kv-value">
                {rule.name} <span className={`tag ${rule.stage === 'PRE' ? 'tag-blue' : 'tag-orange'}`}>{ruleStageLabel[rule.stage]}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state" style={{ padding: '24px 12px' }}>
            <div className="empty-state-text">暂无可用检测规则</div>
          </div>
        )}
      </div>
    ),
  })

  return (
    <div>
      <h1 className="page-title">Agent 管理</h1>
      <p className="page-desc">配置和管理 Agent，发布后自动生成流水线 Pipeline ID</p>

      <div className="toolbar">
        <div className="toolbar-left">
          <Input.Search
            allowClear
            className="toolbar-search"
            placeholder="搜索 Agent 名称"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={() => setPage(1)}
          />
          <Select<AgentType | undefined>
            allowClear
            className="toolbar-filter"
            placeholder="筛选类型"
            value={typeFilter}
            onChange={(value) => {
              setPage(1)
              setTypeFilter(value)
            }}
            options={[
              { label: 'SINGLE', value: 'SINGLE' },
              { label: 'SUB', value: 'SUB' },
              { label: 'ORCHESTRATOR', value: 'ORCHESTRATOR' },
            ]}
          />
          <Select<EnabledFilter | undefined>
            allowClear
            className="toolbar-filter"
            placeholder="筛选状态"
            value={enabledFilter}
            onChange={(value) => {
              setPage(1)
              setEnabledFilter(value)
            }}
            options={[
              { label: '启用', value: 'enabled' },
              { label: '禁用', value: 'disabled' },
            ]}
          />
          <Select<PublishStatus | undefined>
            allowClear
            className="toolbar-filter"
            placeholder="筛选发布状态"
            value={publishStatusFilter}
            onChange={(value) => {
              setPage(1)
              setPublishStatusFilter(value)
            }}
            options={[
              { label: '已发布', value: 'published' },
              { label: '已下架', value: 'draft' },
            ]}
          />
        </div>
        <div className="toolbar-right">
          <Button type="primary" onClick={openCreateDrawer}>
            + 新建 Agent
          </Button>
        </div>
      </div>

      <div className="agent-grid">
        {listLoading ? (
          <div className="page-card" style={{ gridColumn: '1 / -1' }}>
            <div className="table-loading">
              <Spin />
            </div>
          </div>
        ) : agents.length ? (
          agents.map((agent) => (
            <div key={agent.id} className="page-card agent-card">
              <div className="card-header agent-card-header">
                <div className="agent-card-title">{agent.name}</div>
                <span className={`tag ${agentTypeTagClass[agent.agent_type]}`}>{agent.agent_type}</span>
              </div>

              <div className="card-body agent-card-body">
                <div className="agent-card-desc ellipsis-2">{agent.description || '暂无描述'}</div>

                <div className="agent-meta-grid">
                  <div className="agent-meta-item">
                    <div className="agent-meta-label">LLM模型</div>
                    <div className="agent-meta-value">{getModelLabel(agent.llm_model_id, models)}</div>
                  </div>
                  <div className="agent-meta-item">
                    <div className="agent-meta-label">来源平台</div>
                    <div className="agent-meta-value">{getPlatformLabel(agent.source_platform)}</div>
                  </div>
                  <div className="agent-meta-item">
                    <div className="agent-meta-label">工具数量</div>
                    <div className="agent-meta-value">{agent.tool_ids?.length || 0}</div>
                  </div>
                  <div className="agent-meta-item">
                    <div className="agent-meta-label">技能数量</div>
                    <div className="agent-meta-value">{agent.skill_ids?.length || 0}</div>
                  </div>
                </div>

                <div className="agent-status-row">
                  <div className="agent-status-label">启用状态</div>
                  <StatusTag enabled={agent.enabled} />
                </div>
                <div className="agent-status-row">
                  <div className="agent-status-label">发布状态</div>
                  <span className={`tag ${publishStatusTagClass[agent.status]}`}>
                    {agent.status === 'published' ? '已发布' : '草稿'}
                  </span>
                </div>

                {agent.status === 'published' && agent.pipeline_uid && (
                  <div
                    style={{
                      margin: '10px 0 0',
                      padding: '10px 12px',
                      background: 'linear-gradient(135deg, #f0f7ff, #e8f0fe)',
                      border: '1px solid #bfdbfe',
                      borderRadius: 8,
                    }}
                  >
                    <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4, fontWeight: 500 }}>
                      Pipeline ID（用于 API 调用）
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          flex: 1,
                          fontSize: 11,
                          fontFamily: 'ui-monospace, monospace',
                          color: '#1d4ed8',
                          wordBreak: 'break-all',
                          lineHeight: 1.5,
                        }}
                      >
                        {agent.pipeline_uid}
                      </span>
                      <button
                        style={{
                          padding: '2px 8px',
                          fontSize: 11,
                          background: '#2563eb',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          flexShrink: 0,
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          void navigator.clipboard.writeText(agent.pipeline_uid!).then(() => {
                            message.success('Pipeline ID 已复制')
                          })
                        }}
                      >
                        复制
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <div className="agent-card-actions">
                <Button size="small" onClick={() => void openEditDrawer(agent.id)}>
                  配置
                </Button>
                <Button size="small" onClick={() => void handlePublish(agent)}>
                  {agent.status === 'published' ? '下架' : '发布'}
                </Button>
                <Button size="small" onClick={() => void handleToggle(agent)}>
                  {agent.enabled ? '禁用' : '启用'}
                </Button>
                <Popconfirm title="确认删除该 Agent？" onConfirm={() => void handleDelete(agent)}>
                  <Button size="small" danger>
                    删除
                  </Button>
                </Popconfirm>
              </div>
            </div>
          ))
        ) : (
          <div className="page-card" style={{ gridColumn: '1 / -1' }}>
            <div className="empty-state">
              <div className="empty-state-icon">🤖</div>
              <div className="empty-state-text">暂无 Agent，请先创建</div>
            </div>
          </div>
        )}
      </div>

      <div className="pagination-bar" style={{ paddingLeft: 0, paddingRight: 0 }}>
        <span>共 {total} 条记录</span>
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger={false}
          onChange={(nextPage) => setPage(nextPage)}
        />
      </div>

      <Drawer
        title={drawerMode === 'create' ? '新建 Agent' : `配置 Agent${editingAgent ? ` · ${editingAgent.name}` : ''}`}
        width={720}
        open={drawerOpen}
        onClose={closeDrawer}
        destroyOnClose={false}
        footer={
          <div className="drawer-footer">
            <Button onClick={closeDrawer}>取消</Button>
            <Button type="primary" loading={saveLoading} onClick={() => void handleSave()}>
              保存
            </Button>
          </div>
        }
      >
        <Spin spinning={detailLoading || metaLoading}>
          <Form<AgentFormValues> form={form} layout="vertical" initialValues={defaultFormValues}>
            <Tabs className="detail-tabs" activeKey={activeTab} items={tabItems} onChange={setActiveTab} />
          </Form>
        </Spin>
      </Drawer>
    </div>
  )
}
