import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Form, Input, InputNumber, Pagination, Popconfirm, Select, Slider, Spin, Switch, Tabs, message } from 'antd'
import type { TabsProps } from 'antd'
import { agentApi, detectionRuleApi, normalizeDetailResponse, normalizeListResponse, pipelineApi } from '../api'

type PipelineType = 'SINGLE_AGENT' | 'MULTI_AGENT'
type AgentType = 'SINGLE' | 'SUB' | 'ORCHESTRATOR'
type PublishStatus = 'published' | 'draft'
type RuleStage = 'PRE' | 'POST'

interface AgentOption {
  id: number
  name: string
  agent_type: AgentType
  status?: PublishStatus
  enabled: boolean
}

interface DetectionRuleOption {
  id: number
  name: string
  stage: RuleStage
  enabled: boolean
}

interface PipelineAgentRef {
  id: number
  name: string
  agent_type: AgentType
}

interface PipelineRuleRef {
  id: number
  name: string
  stage: RuleStage
}

interface PipelineItem {
  id: number
  name: string
  pipeline_type: PipelineType
  primary_agent_id: number | null
  primary_agent?: PipelineAgentRef
  sub_agents?: PipelineAgentRef[]
  detection_rules?: PipelineRuleRef[]
  detection_rule_ids?: number[]
  sub_agent_ids?: number[]
  route_confidence_threshold: number
  timeout_seconds: number
  stream_output: boolean
  enabled: boolean
}

interface PipelineFormValues {
  name: string
  primary_agent_id?: number
  sub_agent_ids: number[]
  detection_rule_ids: number[]
  route_confidence_threshold: number
  timeout_seconds: number
  stream_output: boolean
}

const defaultFormValues: PipelineFormValues = {
  name: '',
  primary_agent_id: undefined,
  sub_agent_ids: [],
  detection_rule_ids: [],
  route_confidence_threshold: 0.7,
  timeout_seconds: 30,
  stream_output: false,
}

const pipelineTypeTagClass: Record<PipelineType, string> = {
  SINGLE_AGENT: 'tag-blue',
  MULTI_AGENT: 'tag-orange',
}

const isMultiAgent = (subAgentIds: number[]) => subAgentIds.length > 0

const inferPipelineType = (item?: Partial<Pick<PipelineItem, 'pipeline_type' | 'sub_agents' | 'sub_agent_ids'>>): PipelineType => {
  if (Array.isArray(item?.sub_agent_ids) && item.sub_agent_ids.length > 0) {
    return 'MULTI_AGENT'
  }
  if (Array.isArray(item?.sub_agents) && item.sub_agents.length > 0) {
    return 'MULTI_AGENT'
  }
  if (item?.pipeline_type === 'MULTI_AGENT') {
    return 'MULTI_AGENT'
  }
  return 'SINGLE_AGENT'
}

const toFormValues = (detail?: Partial<PipelineItem>): PipelineFormValues => ({
  ...defaultFormValues,
  name: detail?.name || '',
  primary_agent_id: typeof detail?.primary_agent_id === 'number' ? detail.primary_agent_id : undefined,
  sub_agent_ids:
    detail?.sub_agent_ids ||
    (Array.isArray(detail?.sub_agents) ? detail.sub_agents.map((item) => item.id) : []),
  detection_rule_ids:
    detail?.detection_rule_ids ||
    (Array.isArray(detail?.detection_rules) ? detail.detection_rules.map((item) => item.id) : []),
  route_confidence_threshold:
    typeof detail?.route_confidence_threshold === 'number' ? detail.route_confidence_threshold : 0.7,
  timeout_seconds: typeof detail?.timeout_seconds === 'number' ? detail.timeout_seconds : 30,
  stream_output: Boolean(detail?.stream_output),
})

const buildSubmitPayload = (values: PipelineFormValues) => ({
  name: values.name.trim(),
  primary_agent_id: values.primary_agent_id ?? null,
  sub_agent_ids: values.sub_agent_ids,
  detection_rule_ids: values.detection_rule_ids,
  route_confidence_threshold: values.route_confidence_threshold,
  timeout_seconds: values.timeout_seconds,
  stream_output: values.stream_output,
})

const typeDescriptionMap: Record<PipelineType, string> = {
  SINGLE_AGENT: '执行链：意图路由 → 前置检测 → Agent执行 → 后置检测 → 返回',
  MULTI_AGENT: '执行链：智能路由 → 前置检测 → [单子直调 | 多子Planner] → 后置检测 → 返回',
}

export default function PipelinePage() {
  const [form] = Form.useForm<PipelineFormValues>()
  const [pipelines, setPipelines] = useState<PipelineItem[]>([])
  const [agents, setAgents] = useState<AgentOption[]>([])
  const [rules, setRules] = useState<DetectionRuleOption[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [metaLoading, setMetaLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [currentPipeline, setCurrentPipeline] = useState<PipelineItem | null>(null)
  const [activeTab, setActiveTab] = useState('basic')

  const primaryAgentId = Form.useWatch('primary_agent_id', form)
  const subAgentIds = Form.useWatch('sub_agent_ids', form) || []
  const inferredType = isMultiAgent(subAgentIds) ? 'MULTI_AGENT' : 'SINGLE_AGENT'
  const currentEnabled = currentPipeline?.enabled ?? false

  const loadMeta = async () => {
    setMetaLoading(true)
    try {
      const [agentResponse, ruleResponse] = await Promise.all([
        agentApi.list({ page: 1, page_size: 500 }),
        detectionRuleApi.list({ page: 1, page_size: 500 }),
      ])
      setAgents(normalizeListResponse<AgentOption>(agentResponse).items)
      setRules(normalizeListResponse<DetectionRuleOption>(ruleResponse).items)
    } finally {
      setMetaLoading(false)
    }
  }

  const loadPipelines = useCallback(async () => {
    setListLoading(true)
    try {
      const response = await pipelineApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<PipelineItem>(response)
      setPipelines(result.items)
      setTotal(result.total)
    } finally {
      setListLoading(false)
    }
  }, [keyword, page, pageSize])

  const loadPipelineDetail = useCallback(
    async (id: number) => {
      setDetailLoading(true)
      try {
        const detail = normalizeDetailResponse<PipelineItem>(await pipelineApi.get(id))
        setCurrentPipeline(detail)
        setSelectedId(id)
        setIsCreating(false)
        form.setFieldsValue(toFormValues(detail))
      } finally {
        setDetailLoading(false)
      }
    },
    [form],
  )

  useEffect(() => {
    void loadMeta()
  }, [])

  useEffect(() => {
    void loadPipelines()
  }, [loadPipelines])

  useEffect(() => {
    if (isCreating) return
    if (selectedId === null && pipelines.length > 0) {
      void loadPipelineDetail(pipelines[0].id)
      return
    }
    if (selectedId !== null && pipelines.length > 0 && !pipelines.some((item) => item.id === selectedId)) {
      const next = pipelines[0]
      if (next) {
        void loadPipelineDetail(next.id)
      } else {
        setSelectedId(null)
        setCurrentPipeline(null)
      }
    }
    if (pipelines.length === 0 && !isCreating) {
      setSelectedId(null)
      setCurrentPipeline(null)
    }
  }, [isCreating, loadPipelineDetail, pipelines, selectedId])

  const publishedAgents = useMemo(
    () => agents.filter((item) => item.status === 'published'),
    [agents],
  )

  const primaryAgentOptions = useMemo(() => publishedAgents, [publishedAgents])

  const subAgentOptions = useMemo(
    () =>
      publishedAgents.filter(
        (item) => (item.agent_type === 'SINGLE' || item.agent_type === 'SUB') && item.id !== primaryAgentId,
      ),
    [primaryAgentId, publishedAgents],
  )

  const openCreate = () => {
    setSelectedId(null)
    setCurrentPipeline(null)
    setIsCreating(true)
    setActiveTab('basic')
    form.resetFields()
    form.setFieldsValue(defaultFormValues)
  }

  const handleSelect = async (id: number) => {
    setActiveTab('basic')
    await loadPipelineDetail(id)
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    const payload = buildSubmitPayload(values)
    setSaveLoading(true)
    try {
      if (isCreating || selectedId === null) {
        const result = normalizeDetailResponse<{ id?: number }>(await pipelineApi.create(payload))
        message.success('操作成功')
        await loadPipelines()
        if (typeof result.id === 'number') {
          await loadPipelineDetail(result.id)
        } else {
          setIsCreating(false)
        }
      } else {
        await pipelineApi.update(selectedId, payload)
        message.success('操作成功')
        await Promise.all([loadPipelines(), loadPipelineDetail(selectedId)])
      }
    } finally {
      setSaveLoading(false)
    }
  }

  const handleToggle = async () => {
    if (selectedId === null || currentPipeline === null) return
    setActionLoading(true)
    try {
      await pipelineApi.toggle(selectedId, !currentEnabled)
      message.success(!currentEnabled ? '已启用' : '已禁用')
      await Promise.all([loadPipelines(), loadPipelineDetail(selectedId)])
    } finally {
      setActionLoading(false)
    }
  }

  const handleDelete = async () => {
    if (selectedId === null) return
    setActionLoading(true)
    try {
      await pipelineApi.delete(selectedId)
      message.success('删除成功')
      setSelectedId(null)
      setCurrentPipeline(null)
      setIsCreating(false)
      form.resetFields()
      await loadPipelines()
    } finally {
      setActionLoading(false)
    }
  }

  const currentTypeLabel = inferredType === 'MULTI_AGENT' ? '多 Agent 编排' : '单 Agent'
  const detailPipelineId = currentPipeline?.id

  const tabItems: TabsProps['items'] = [
    {
      key: 'basic',
      label: '基础配置',
      children: (
        <div className="form-section">
          <div className="form-grid-2">
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入流水线名称' }]}>
              <Input placeholder="请输入流水线名称" />
            </Form.Item>
            <Form.Item label="超时秒数" name="timeout_seconds" rules={[{ required: true, message: '请输入超时秒数' }]}>
              <InputNumber min={5} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item
            label="主 Agent"
            name="primary_agent_id"
            rules={[
              {
                validator: async (_, value: number | undefined) => {
                  if (inferredType === 'SINGLE_AGENT' && typeof value !== 'number') {
                    throw new Error('单 Agent 模式下请选择主 Agent')
                  }
                },
              },
            ]}
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              loading={metaLoading}
              placeholder={inferredType === 'SINGLE_AGENT' ? '请选择主 Agent' : '请选择编排 Agent'}
              options={primaryAgentOptions.map((item) => ({
                label: `${item.name} (${item.agent_type})`,
                value: item.id,
              }))}
            />
          </Form.Item>
          <div style={{ color: '#6b7280', fontSize: 12, marginTop: -8, marginBottom: 16 }}>
            单 Agent 模式下必填；多 Agent 模式下可选为编排 Agent。
          </div>

          <Form.Item label="子 Agent" name="sub_agent_ids">
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              loading={metaLoading}
              placeholder="选择子 Agent 后自动切换为多 Agent 编排模式"
              options={subAgentOptions.map((item) => ({
                label: `${item.name} (${item.agent_type})`,
                value: item.id,
              }))}
            />
          </Form.Item>
          <div style={{ color: '#6b7280', fontSize: 12, marginTop: -8, marginBottom: 16 }}>
            选择子 Agent 后自动切换为多 Agent 编排模式
          </div>

          <Form.Item label="检测规则" name="detection_rule_ids">
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              loading={metaLoading}
              placeholder="请选择关联检测规则"
              options={rules.map((rule) => ({
                label: `${rule.name} ${rule.stage}`,
                value: rule.id,
              }))}
              optionRender={(option) => {
                const rule = rules.find((item) => item.id === Number(option.value))
                if (!rule) {
                  return <span>{String(option.label)}</span>
                }
                return (
                  <span>
                    {rule.name} <span className={`tag ${rule.stage === 'PRE' ? 'tag-blue' : 'tag-orange'}`}>{rule.stage}</span>
                  </span>
                )
              }}
            />
          </Form.Item>

          {inferredType === 'MULTI_AGENT' ? (
            <div className="form-grid-2">
              <Form.Item label="路由置信阈值" name="route_confidence_threshold">
                <Slider min={0} max={1} step={0.01} />
              </Form.Item>
              <Form.Item label="流式输出" name="stream_output" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </div>
          ) : (
            <Form.Item label="流式输出" name="stream_output" valuePropName="checked">
              <Switch checkedChildren="开启" unCheckedChildren="关闭" />
            </Form.Item>
          )}
        </div>
      ),
    },
    {
      key: 'type',
      label: '类型说明',
      children: (
        <div className="form-section">
          <div style={{ color: '#6b7280', fontSize: 13, marginBottom: 12 }}>
            当前类型由子 Agent 配置自动推断，无需手动指定。
          </div>
          <pre className="code-block">{`当前类型：${currentTypeLabel}\n\n${typeDescriptionMap[inferredType]}`}</pre>
        </div>
      ),
    },
    {
      key: 'examples',
      label: '调用示例',
      children: detailPipelineId ? (
        <div className="form-section">
          <div className="form-section-title">非流式调用</div>
          <pre className="code-block">{`curl -X POST http://localhost:8000/api/v1/query \\
  -H 'Content-Type: application/json' \\
  -d '{
    "query": "你的问题",
    "pipeline_id": ${detailPipelineId},
    "stream": false,
    "session_id": "可选会话ID"
  }'`}</pre>

          <div className="form-section-title" style={{ marginTop: 20 }}>
            流式调用（SSE）
          </div>
          <pre className="code-block">{`curl -N -X POST http://localhost:8000/api/v1/query \\
  -H 'Content-Type: application/json' \\
  -d '{
    "query": "你的问题",
    "pipeline_id": ${detailPipelineId},
    "stream": true
  }'`}</pre>

          <div className="form-section-title" style={{ marginTop: 20 }}>
            响应格式
          </div>
          <pre className="code-block">{`// 非流式
{
  "code": 0,
  "data": {
    "answer": "Agent回复内容",
    "pipeline_type": "${inferredType}",
    "tools_called": ["tool_name"],
    "session_id": "sess-xxx",
    "latency_ms": 1200
  }
}
// 流式 SSE 事件
data: {"type":"answer","content":"增量文本"}
data: {"type":"done","answer":"完整回复","pipeline_id":${detailPipelineId}}`}</pre>
        </div>
      ) : (
        <div className="empty-state" style={{ minHeight: 280 }}>
          <div className="empty-state-icon">🚀</div>
          <div className="empty-state-text">请先保存流水线以查看调用示例</div>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="page-title">流水线管理</div>
      <div className="page-desc">统一编排主 Agent、子 Agent 与检测规则，形成可直接调用的执行流水线。</div>

      <div className="split-layout">
        <div className="page-card split-list">
          <div className="card-header">
            <div className="card-header-title">流水线列表</div>
            <Button type="primary" onClick={openCreate}>
              + 新建
            </Button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div style={{ padding: 16, borderBottom: '1px solid var(--border)' }}>
              <Input.Search
                allowClear
                placeholder="搜索流水线"
                style={{ width: '100%' }}
                onSearch={(value) => {
                  setPage(1)
                  setKeyword(value)
                }}
              />
            </div>

            {listLoading ? (
              <div className="table-loading">
                <Spin />
              </div>
            ) : pipelines.length ? (
              pipelines.map((pipeline) => {
                const pipelineType = inferPipelineType(pipeline)
                return (
                  <div
                    key={pipeline.id}
                    className={`list-item${!isCreating && selectedId === pipeline.id ? ' active' : ''}`}
                    onClick={() => void handleSelect(pipeline.id)}
                  >
                    <div className="list-item-name">{pipeline.name}</div>
                    <div className="list-item-sub">{pipeline.primary_agent?.name || '未配置主 Agent'}</div>
                    <div className="list-item-tags">
                      <span className={`tag ${pipelineTypeTagClass[pipelineType]}`}>
                        {pipelineType === 'MULTI_AGENT' ? '多 Agent 编排' : '单 Agent'}
                      </span>
                      <span className={`tag ${pipeline.enabled ? 'tag-green' : 'tag-gray'}`}>
                        {pipeline.enabled ? '启用' : '禁用'}
                      </span>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🚀</div>
                <div className="empty-state-text">暂无流水线</div>
              </div>
            )}

            <div className="pagination-bar">
              <span>共 {total} 条记录</span>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                size="small"
                showSizeChanger
                pageSizeOptions={[10, 20, 50, 100]}
                onChange={(nextPage, nextPageSize) => {
                  setPage(nextPage)
                  setPageSize(nextPageSize)
                }}
              />
            </div>
          </div>
        </div>

        <div className="page-card split-detail">
          {!isCreating && selectedId === null ? (
            <div className="empty-state" style={{ minHeight: 480 }}>
              <div className="empty-state-icon">←</div>
              <div className="empty-state-text">请从左侧选择流水线</div>
            </div>
          ) : (
            <Spin spinning={detailLoading || metaLoading}>
              <div className="agent-detail-header">
                <div>
                  <div className="agent-detail-title">{isCreating ? '新建流水线' : currentPipeline?.name || '流水线配置'}</div>
                  <div className="agent-detail-subtitle">配置主 Agent、子 Agent、检测规则和调用参数。</div>
                </div>
                <div className="list-item-tags">
                  <span className={`tag ${pipelineTypeTagClass[inferredType]}`}>{currentTypeLabel}</span>
                </div>
              </div>

              <Form<PipelineFormValues> form={form} layout="vertical" initialValues={defaultFormValues}>
                <Tabs className="detail-tabs" activeKey={activeTab} items={tabItems} onChange={setActiveTab} />
              </Form>

              <div className="action-bar">
                <div className="action-bar-left">
                  {!isCreating ? (
                    <Popconfirm title="确认删除该流水线？" onConfirm={() => void handleDelete()}>
                      <Button danger loading={actionLoading}>
                        删除
                      </Button>
                    </Popconfirm>
                  ) : null}
                </div>
                <div className="action-bar-right">
                  {!isCreating ? (
                    <Button loading={actionLoading} onClick={() => void handleToggle()}>
                      {currentEnabled ? '禁用' : '启用'}
                    </Button>
                  ) : null}
                  <Button type="primary" loading={saveLoading} onClick={() => void handleSave()}>
                    保存
                  </Button>
                </div>
              </div>
            </Spin>
          )}
        </div>
      </div>
    </div>
  )
}
