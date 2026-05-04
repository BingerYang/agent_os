import { useEffect, useMemo, useState } from 'react'
import { Button, Drawer, Form, Input, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import { agentApi, normalizeDetailResponse, normalizeListResponse, workflowApi } from '../api'

type TriggerMode = 'manual' | 'schedule' | 'webhook'

interface WorkflowStep {
  name: string
  agent_id?: number
  input_mapping?: Record<string, unknown>
}

interface WorkflowConfig {
  trigger_mode?: TriggerMode
  steps?: WorkflowStep[]
}

interface WorkflowItem {
  id: number
  name: string
  description?: string
  config?: string | WorkflowConfig
  steps?: WorkflowStep[]
  enabled: boolean
}

interface AgentOption {
  id: number
  name: string
}

interface WorkflowFormValues {
  name: string
  description?: string
  trigger_mode: TriggerMode
  step1_name?: string
  step1_agent_id?: number
  step1_input_mapping?: string
  step2_name?: string
  step2_agent_id?: number
  step2_input_mapping?: string
  raw_config?: string
  enabled: boolean
}

const actionButtonStyle: React.CSSProperties = {
  color: '#2563eb',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontSize: 12,
  padding: '2px 6px',
}

const dangerButtonStyle: React.CSSProperties = {
  ...actionButtonStyle,
  color: '#ef4444',
}

const stringifyConfig = (value: WorkflowItem['config']) => {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
  return '{}'
}

const parseWorkflowConfig = (value: WorkflowItem['config']) => {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value) as WorkflowConfig
    } catch {
      return {}
    }
  }
  return (value || {}) as WorkflowConfig
}

const stringifyMapping = (value?: Record<string, unknown>) => JSON.stringify(value || {}, null, 2)

const parseJsonText = (value?: string) => {
  if (!value?.trim()) return {}
  return JSON.parse(value)
}

export default function WorkflowPage() {
  const [form] = Form.useForm<WorkflowFormValues>()
  const [list, setList] = useState<WorkflowItem[]>([])
  const [agentOptions, setAgentOptions] = useState<AgentOption[]>([])
  const [loading, setLoading] = useState(false)
  const [agentLoading, setAgentLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [keyword, setKeyword] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  const loadAgents = async () => {
    setAgentLoading(true)
    try {
      const response = await agentApi.list({ page: 1, page_size: 500 })
      const result = normalizeListResponse<AgentOption>(response)
      setAgentOptions(result.items)
    } finally {
      setAgentLoading(false)
    }
  }

  const loadList = async () => {
    setLoading(true)
    try {
      const response = await workflowApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<WorkflowItem>(response)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAgents()
  }, [])

  useEffect(() => {
    void loadList()
  }, [page, pageSize, keyword])

  const openCreate = () => {
    setEditingId(null)
    form.resetFields()
    form.setFieldsValue({
      trigger_mode: 'manual',
      step1_input_mapping: '{}',
      step2_input_mapping: '{}',
      raw_config: '{}',
      enabled: true,
    })
    setDrawerOpen(true)
  }

  const openEdit = async (record: WorkflowItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    const detail = normalizeDetailResponse<WorkflowItem>(await workflowApi.get(record.id))
    const config = parseWorkflowConfig(detail.config)
    const steps = Array.isArray(config.steps) ? config.steps : detail.steps || []
    form.setFieldsValue({
      name: detail.name,
      description: detail.description,
      trigger_mode: config.trigger_mode || 'manual',
      step1_name: steps[0]?.name,
      step1_agent_id: steps[0]?.agent_id,
      step1_input_mapping: stringifyMapping(steps[0]?.input_mapping),
      step2_name: steps[1]?.name,
      step2_agent_id: steps[1]?.agent_id,
      step2_input_mapping: stringifyMapping(steps[1]?.input_mapping),
      raw_config: stringifyConfig(detail.config),
      enabled: detail.enabled,
    })
  }

  const buildPayload = async () => {
    const values = await form.validateFields()
    const steps: WorkflowStep[] = [
      values.step1_name
        ? {
            name: values.step1_name.trim(),
            agent_id: values.step1_agent_id,
            input_mapping: parseJsonText(values.step1_input_mapping),
          }
        : null,
      values.step2_name
        ? {
            name: values.step2_name.trim(),
            agent_id: values.step2_agent_id,
            input_mapping: parseJsonText(values.step2_input_mapping),
          }
        : null,
    ].filter(Boolean) as WorkflowStep[]

    const baseConfig = parseJsonText(values.raw_config)
    const payload = {
      name: values.name.trim(),
      description: values.description?.trim() || undefined,
      config: {
        ...baseConfig,
        trigger_mode: values.trigger_mode,
        steps,
      },
      enabled: values.enabled,
    }
    return payload
  }

  const handleSubmit = async () => {
    setSaving(true)
    try {
      const payload = await buildPayload()
      if (editingId === null) {
        await workflowApi.create(payload)
      } else {
        await workflowApi.update(editingId, payload)
      }
      message.success('操作成功')
      setDrawerOpen(false)
      await loadList()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: WorkflowItem) => {
    await workflowApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await workflowApi.delete(id)
    message.success('操作成功')
    if (list.length === 1 && page > 1) {
      setPage((current) => current - 1)
      return
    }
    await loadList()
  }

  const paginationConfig: PaginationProps = {
    current: page,
    pageSize,
    total,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
    onChange: (nextPage, nextPageSize) => {
      setPage(nextPage)
      setPageSize(nextPageSize)
    },
  }

  const workflowRows = useMemo(
    () =>
      list.map((item) => {
        const config = parseWorkflowConfig(item.config)
        const steps = Array.isArray(config.steps) ? config.steps : item.steps || []
        return {
          ...item,
          trigger_mode: config.trigger_mode || 'manual',
          step_count: steps.length,
        }
      }),
    [list],
  )

  return (
    <div>
      <div className="page-title">工作流</div>
      <div className="page-desc">配置多步骤执行流程，管理触发方式、步骤 Agent 绑定及整体 JSON 配置。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">工作流列表</div>
          <div className="toolbar-right">
            <Button type="primary" onClick={openCreate}>
              + 新建工作流
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索工作流"
                onSearch={(value) => {
                  setPage(1)
                  setKeyword(value)
                }}
              />
            </div>
          </div>

          {loading ? (
            <div className="table-loading">
              <Spin />
            </div>
          ) : (
            <>
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>名称</th>
                      <th>描述</th>
                      <th>Agent数</th>
                      <th>触发方式</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {workflowRows.map((record) => (
                      <tr key={record.id}>
                        <td style={{ fontWeight: 600 }}>{record.name}</td>
                        <td>{record.description || '-'}</td>
                        <td>{record.step_count}</td>
                        <td>
                          <span className="tag tag-blue">{record.trigger_mode}</span>
                        </td>
                        <td>
                          <StatusTag enabled={record.enabled} />
                        </td>
                        <td>
                          <div className="actions">
                            <button type="button" style={actionButtonStyle} onClick={() => void openEdit(record)}>
                              配置
                            </button>
                            <button type="button" style={actionButtonStyle} onClick={() => void handleToggle(record)}>
                              {record.enabled ? '禁用' : '启用'}
                            </button>
                            <Popconfirm title="确认删除该工作流？" onConfirm={() => void handleDelete(record.id)}>
                              <button type="button" style={dangerButtonStyle}>
                                删除
                              </button>
                            </Popconfirm>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!workflowRows.length ? (
                      <tr>
                        <td colSpan={6}>
                          <div className="empty-state">
                            <div className="empty-state-icon">🔄</div>
                            <div className="empty-state-text">暂无工作流</div>
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="pagination-bar">
                <span>共 {total} 条记录</span>
                <Pagination {...paginationConfig} />
              </div>
            </>
          )}
        </div>
      </div>

      <Drawer
        title={editingId === null ? '新建工作流' : '编辑工作流'}
        width={620}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
        extra={
          <div className="drawer-footer">
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={() => void handleSubmit()}>
              保存
            </Button>
          </div>
        }
      >
        <Form<WorkflowFormValues> form={form} layout="vertical" initialValues={{ trigger_mode: 'manual', enabled: true }}>
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入工作流名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入工作流描述" />
          </Form.Item>
          <Form.Item
            label="触发方式"
            name="trigger_mode"
            rules={[{ required: true, message: '请选择触发方式' }]}
          >
            <Select
              options={[
                { label: 'manual', value: 'manual' },
                { label: 'schedule', value: 'schedule' },
                { label: 'webhook', value: 'webhook' },
              ]}
            />
          </Form.Item>

          <div className="form-section">
            <div className="form-section-title">步骤配置</div>
            <div className="mini-card">
              <div className="mini-card-title">步骤 1</div>
              <Form.Item label="步骤名" name="step1_name">
                <Input placeholder="例如 意图识别" />
              </Form.Item>
              <Form.Item label="Agent 选择" name="step1_agent_id">
                <Select
                  allowClear
                  loading={agentLoading}
                  options={agentOptions.map((item) => ({
                    label: item.name,
                    value: item.id,
                  }))}
                />
              </Form.Item>
              <Form.Item
                label="输入映射(JSON)"
                name="step1_input_mapping"
                rules={[
                  {
                    validator: async (_, value?: string) => {
                      if (!value?.trim()) return
                      JSON.parse(value)
                    },
                  },
                ]}
              >
                <Input.TextArea rows={4} className="mono-textarea" placeholder='例如 {"query":"{{input}}"}' />
              </Form.Item>
            </div>

            <div className="mini-card">
              <div className="mini-card-title">步骤 2</div>
              <Form.Item label="步骤名" name="step2_name">
                <Input placeholder="例如 结果汇总" />
              </Form.Item>
              <Form.Item label="Agent 选择" name="step2_agent_id">
                <Select
                  allowClear
                  loading={agentLoading}
                  options={agentOptions.map((item) => ({
                    label: item.name,
                    value: item.id,
                  }))}
                />
              </Form.Item>
              <Form.Item
                label="输入映射(JSON)"
                name="step2_input_mapping"
                rules={[
                  {
                    validator: async (_, value?: string) => {
                      if (!value?.trim()) return
                      JSON.parse(value)
                    },
                  },
                ]}
              >
                <Input.TextArea rows={4} className="mono-textarea" placeholder='例如 {"result":"{{step1.output}}"}' />
              </Form.Item>
            </div>
          </div>

          <Form.Item
            label="整体 JSON 配置"
            name="raw_config"
            rules={[
              {
                validator: async (_, value?: string) => {
                  if (!value?.trim()) return
                  JSON.parse(value)
                },
              },
            ]}
          >
            <Input.TextArea rows={10} className="mono-textarea" placeholder="请输入完整 JSON 配置" />
          </Form.Item>
          <Form.Item label="启用状态" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
