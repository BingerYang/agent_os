import { useEffect, useState } from 'react'
import { Button, Drawer, Form, Input, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import { normalizeDetailResponse, normalizeListResponse, skillApi, toolApi } from '../api'

type TriggerType = 'keyword' | 'intent' | 'manual'

interface SkillItem {
  id: number
  name: string
  description?: string
  trigger_condition?: string
  category?: string
  author?: string
  version?: string
  tool_ids?: number[]
  enabled: boolean
}

interface ToolOption {
  id: number
  display_name?: string
  name: string
}

interface SkillFormValues {
  name: string
  description?: string
  trigger_type: TriggerType
  tool_ids?: number[]
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

const inferTriggerType = (skill: SkillItem): TriggerType => {
  const text = `${skill.category || ''} ${skill.trigger_condition || ''}`.toLowerCase()
  if (text.includes('intent')) return 'intent'
  if (text.includes('manual')) return 'manual'
  return 'keyword'
}

const triggerTagClass: Record<TriggerType, string> = {
  keyword: 'tag-blue',
  intent: 'tag-orange',
  manual: 'tag-gray',
}

const triggerText: Record<TriggerType, string> = {
  keyword: 'keyword',
  intent: 'intent',
  manual: 'manual',
}

export default function SkillPage() {
  const [form] = Form.useForm<SkillFormValues>()
  const [list, setList] = useState<SkillItem[]>([])
  const [toolOptions, setToolOptions] = useState<ToolOption[]>([])
  const [loading, setLoading] = useState(false)
  const [toolLoading, setToolLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [keyword, setKeyword] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  const loadTools = async () => {
    setToolLoading(true)
    try {
      const response = await toolApi.list({ page: 1, page_size: 500 })
      const result = normalizeListResponse<ToolOption>(response)
      setToolOptions(result.items)
    } finally {
      setToolLoading(false)
    }
  }

  const loadList = async () => {
    setLoading(true)
    try {
      const response = await skillApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<SkillItem>(response)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadTools()
  }, [])

  useEffect(() => {
    void loadList()
  }, [page, pageSize, keyword])

  const openCreate = () => {
    setEditingId(null)
    form.resetFields()
    form.setFieldsValue({ trigger_type: 'manual', tool_ids: [], enabled: true })
    setDrawerOpen(true)
  }

  const openEdit = async (record: SkillItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    const detail = normalizeDetailResponse<SkillItem>(await skillApi.get(record.id))
    form.setFieldsValue({
      name: detail.name,
      description: detail.description,
      trigger_type: inferTriggerType(detail),
      tool_ids: detail.tool_ids || [],
      enabled: detail.enabled,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      name: values.name.trim(),
      description: values.description?.trim() || undefined,
      trigger_condition: `trigger_type:${values.trigger_type}`,
      category: values.trigger_type,
      author: '系统官方',
      version: 'v1.0.0',
      tool_ids: values.tool_ids || [],
      enabled: values.enabled,
    }
    setSaving(true)
    try {
      if (editingId === null) {
        await skillApi.create(payload)
      } else {
        await skillApi.update(editingId, payload)
      }
      message.success('操作成功')
      setDrawerOpen(false)
      await loadList()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: SkillItem) => {
    await skillApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await skillApi.delete(id)
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
      <div className="page-title">技能管理</div>
      <div className="page-desc">管理可复用技能定义与工具绑定关系，统一维护触发方式、描述信息与启用状态。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">技能列表</div>
          <div className="toolbar-right">
            <Button type="primary" onClick={openCreate}>
              + 新建技能
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索技能名称"
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
                      <th>触发类型</th>
                      <th>工具数量</th>
                      <th>技能数量</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((record) => {
                      const triggerType = inferTriggerType(record)
                      return (
                        <tr key={record.id}>
                          <td style={{ fontWeight: 600 }}>{record.name}</td>
                          <td>
                            <div
                              style={{
                                maxWidth: 120,
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {record.description || '-'}
                            </div>
                          </td>
                          <td>
                            <span className={`tag ${triggerTagClass[triggerType]}`}>{triggerText[triggerType]}</span>
                          </td>
                          <td>{record.tool_ids?.length || 0}</td>
                          <td>1</td>
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
                              <Popconfirm title="确认删除该技能？" onConfirm={() => void handleDelete(record.id)}>
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
                            <div className="empty-state-icon">⚡</div>
                            <div className="empty-state-text">暂无技能</div>
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
        title={editingId === null ? '新建技能' : '编辑技能'}
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
        <Form<SkillFormValues> form={form} layout="vertical" initialValues={{ trigger_type: 'manual', enabled: true }}>
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入技能名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入技能描述" />
          </Form.Item>
          <Form.Item
            label="触发类型"
            name="trigger_type"
            rules={[{ required: true, message: '请选择触发类型' }]}
          >
            <Select
              options={[
                { label: 'keyword', value: 'keyword' },
                { label: 'intent', value: 'intent' },
                { label: 'manual', value: 'manual' },
              ]}
            />
          </Form.Item>
          <Form.Item label="工具绑定" name="tool_ids">
            <Select
              mode="multiple"
              loading={toolLoading}
              placeholder="请选择要绑定的工具"
              options={toolOptions.map((item) => ({
                label: item.display_name || item.name,
                value: item.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
