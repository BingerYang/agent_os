import { useEffect, useState } from 'react'
import { Button, Drawer, Form, Input, InputNumber, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import { detectionRuleApi, normalizeDetailResponse, normalizeListResponse } from '../api'

type ActionType = 'block' | 'rewrite' | 'notify' | 'passthrough'
type RuleStage = 'PRE' | 'POST'
type RuleType = 'keyword' | 'llm_judge'

interface PipelineItem {
  id: number
  name: string
  stage: RuleStage
  rule_type: RuleType
  rule_content?: Record<string, unknown>
  reject_message?: string
  priority: number
  enabled: boolean
}

interface PipelineFormValues {
  name: string
  description?: string
  trigger_condition?: string
  action_type: ActionType
  action_content?: string
  priority: number
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

const actionLabelMap: Record<ActionType, string> = {
  block: '拦截',
  rewrite: '改写',
  notify: '通知',
  passthrough: '直通',
}

const inferActionType = (record: PipelineItem): ActionType => {
  const content = `${record.reject_message || ''}`.toLowerCase()
  if (content.includes('rewrite')) return 'rewrite'
  if (content.includes('notify')) return 'notify'
  if (content.includes('passthrough')) return 'passthrough'
  return 'block'
}

const toRuleContent = (triggerCondition?: string, actionContent?: string) => ({
  condition: triggerCondition?.trim() || '',
  action: actionContent?.trim() || '',
})

export default function DetectionRulesPage() {
  const [form] = Form.useForm<PipelineFormValues>()
  const [list, setList] = useState<PipelineItem[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [keyword, setKeyword] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  const loadList = async () => {
    setLoading(true)
    try {
      const response = await detectionRuleApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<PipelineItem>(response)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadList()
  }, [page, pageSize, keyword])

  const openCreate = () => {
    setEditingId(null)
    form.resetFields()
    form.setFieldsValue({ action_type: 'block', priority: 100, enabled: true })
    setDrawerOpen(true)
  }

  const openEdit = async (record: PipelineItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    const detail = normalizeDetailResponse<PipelineItem>(await detectionRuleApi.get(record.id))
    const content = (detail.rule_content || {}) as Record<string, unknown>
    form.setFieldsValue({
      name: detail.name,
      description: detail.stage === 'PRE' ? '前置检测规则' : '后置检测规则',
      trigger_condition: String(content.condition || ''),
      action_type: inferActionType(detail),
      action_content: detail.reject_message || String(content.action || ''),
      priority: detail.priority,
      enabled: detail.enabled,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      name: values.name.trim(),
      stage: 'PRE',
      rule_type: 'keyword',
      rule_content: toRuleContent(values.trigger_condition, values.action_content),
      reject_message: `${values.action_type}:${values.action_content?.trim() || ''}`,
      priority: values.priority,
      enabled: values.enabled,
    }
    setSaving(true)
    try {
      if (editingId === null) {
        await detectionRuleApi.create(payload)
      } else {
        await detectionRuleApi.update(editingId, payload)
      }
      message.success('操作成功')
      setDrawerOpen(false)
      await loadList()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: PipelineItem) => {
    await detectionRuleApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await detectionRuleApi.delete(id)
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

  return (
    <div>
      <div className="page-title">检测规则</div>
      <div className="page-desc">统一维护前后置检测规则，支持优先级控制、动作策略配置与启停管理。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">规则列表</div>
          <div className="toolbar-right">
            <Button type="primary" onClick={openCreate}>
              + 新建规则
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索检测规则"
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
                      <th>触发条件</th>
                      <th>动作</th>
                      <th>优先级</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((record) => {
                      const content = (record.rule_content || {}) as Record<string, unknown>
                      const actionType = inferActionType(record)
                      return (
                        <tr key={record.id}>
                          <td style={{ fontWeight: 600 }}>{record.name}</td>
                          <td>{record.stage === 'PRE' ? '前置检测' : '后置检测'}</td>
                          <td>
                            <div
                              style={{
                                maxWidth: 180,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {String(content.condition || '-')}
                            </div>
                          </td>
                          <td>
                            <div
                              style={{
                                maxWidth: 180,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {actionLabelMap[actionType]}：{record.reject_message || String(content.action || '-')}
                            </div>
                          </td>
                          <td>{record.priority}</td>
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
                              <Popconfirm title="确认删除该规则？" onConfirm={() => void handleDelete(record.id)}>
                                <button type="button" style={dangerButtonStyle}>
                                  删除
                                </button>
                              </Popconfirm>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                    {!list.length ? (
                      <tr>
                        <td colSpan={7}>
                          <div className="empty-state">
                            <div className="empty-state-icon">🛡️</div>
                            <div className="empty-state-text">暂无检测规则</div>
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
        title={editingId === null ? '新建检测规则' : '编辑检测规则'}
        width={560}
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
        <Form<PipelineFormValues> form={form} layout="vertical" initialValues={{ action_type: 'block', priority: 100, enabled: true }}>
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="请输入规则描述" />
          </Form.Item>
          <Form.Item label="触发条件" name="trigger_condition">
            <Input.TextArea
              rows={4}
              className="mono-textarea"
              placeholder={'示例：\n包含敏感关键词\n请求命中某类风险意图\n输入超过指定长度'}
            />
          </Form.Item>
          <Form.Item
            label="动作类型"
            name="action_type"
            rules={[{ required: true, message: '请选择动作类型' }]}
          >
            <Select
              options={[
                { label: '拦截', value: 'block' },
                { label: '改写', value: 'rewrite' },
                { label: '通知', value: 'notify' },
                { label: '直通', value: 'passthrough' },
              ]}
            />
          </Form.Item>
          <Form.Item label="动作内容" name="action_content">
            <Input.TextArea rows={4} className="mono-textarea" placeholder="请输入动作执行内容或返回消息" />
          </Form.Item>
          <Form.Item label="优先级" name="priority">
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="启用状态" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
