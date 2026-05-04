import { useEffect, useState } from 'react'
import { Button, Drawer, Form, Input, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import { mcpServerApi, normalizeDetailResponse, normalizeListResponse } from '../api'

type TransportType = 'STDIO' | 'HTTP_SSE' | 'stdio' | 'sse' | 'http'
type ServerStatus = 'UNKNOWN' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'

interface MCPServerItem {
  id: number
  name: string
  display_name: string
  description?: string
  transport_type: TransportType
  command?: string
  endpoint_url?: string
  env_vars?: Record<string, string> | string | null
  auth_type?: string
  auth_config?: Record<string, unknown> | null
  auto_connect?: boolean
  enabled: boolean
  status?: ServerStatus
  tool_count?: number
  last_connected_at?: string
}

interface MCPServerFormValues {
  name: string
  display_name: string
  description?: string
  transport_type: 'STDIO' | 'HTTP_SSE'
  command?: string
  endpoint_url?: string
  env_vars?: string
  auto_connect?: boolean
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

const transportDisplayMap: Record<string, string> = {
  STDIO: 'stdio',
  HTTP_SSE: 'sse/http',
  stdio: 'stdio',
  sse: 'sse',
  http: 'http',
}

const transportTagClass = (transportType: TransportType) => {
  const value = String(transportType).toUpperCase()
  if (value === 'STDIO') return 'tag-blue'
  if (value === 'HTTP_SSE') return 'tag-purple'
  if (value === 'HTTP') return 'tag-orange'
  return 'tag-blue'
}

const connectionTag = (status?: ServerStatus) => {
  if (status === 'CONNECTED') return <span className="tag tag-green">已连接</span>
  if (status === 'ERROR') return <span className="tag tag-red">异常</span>
  if (status === 'DISCONNECTED') return <span className="tag tag-orange">未连接</span>
  return <span className="tag tag-gray">未知</span>
}

const stringifyEnvVars = (value: MCPServerItem['env_vars']) => {
  if (typeof value === 'string') return value
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
  return '{}'
}

const parseTransport = (value?: TransportType) => {
  const normalized = String(value || 'HTTP_SSE').toUpperCase()
  return normalized === 'STDIO' ? 'STDIO' : 'HTTP_SSE'
}

export default function MCPServersPage() {
  const [form] = Form.useForm<MCPServerFormValues>()
  const [list, setList] = useState<MCPServerItem[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [keyword, setKeyword] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)

  const transportType = Form.useWatch('transport_type', form)

  const loadList = async () => {
    setLoading(true)
    try {
      const response = await mcpServerApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<MCPServerItem>(response)
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
    form.setFieldsValue({
      transport_type: 'STDIO',
      auto_connect: false,
      enabled: true,
      env_vars: '{}',
    })
    setDrawerOpen(true)
  }

  const openEdit = async (record: MCPServerItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    const detail = normalizeDetailResponse<MCPServerItem>(await mcpServerApi.get(record.id))
    form.setFieldsValue({
      name: detail.name,
      display_name: detail.display_name,
      description: detail.description,
      transport_type: parseTransport(detail.transport_type),
      command: detail.command,
      endpoint_url: detail.endpoint_url,
      env_vars: stringifyEnvVars(detail.env_vars),
      auto_connect: detail.auto_connect,
      enabled: detail.enabled,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      transport_type: values.transport_type,
      command: values.transport_type === 'STDIO' ? values.command?.trim() || undefined : undefined,
      endpoint_url:
        values.transport_type === 'HTTP_SSE' ? values.endpoint_url?.trim() || undefined : undefined,
      env_vars: values.env_vars ? JSON.parse(values.env_vars) : {},
      auth_type: 'NONE',
      auth_config: null,
    }
    setSaving(true)
    try {
      if (editingId === null) {
        await mcpServerApi.create(payload)
      } else {
        await mcpServerApi.update(editingId, payload)
      }
      message.success('操作成功')
      setDrawerOpen(false)
      await loadList()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: MCPServerItem) => {
    await mcpServerApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await mcpServerApi.delete(id)
    message.success('操作成功')
    if (list.length === 1 && page > 1) {
      setPage((current) => current - 1)
      return
    }
    await loadList()
  }

  const handleConnect = async (id: number) => {
    setActionLoadingId(id)
    try {
      await mcpServerApi.connect(id)
      message.success('连接成功')
      await loadList()
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleDiscover = async (id: number) => {
    setActionLoadingId(id)
    try {
      await mcpServerApi.discover(id)
      message.success('工具发现完成')
      await loadList()
    } finally {
      setActionLoadingId(null)
    }
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
      <div className="page-title">MCP Server</div>
      <div className="page-desc">管理 MCP Server 连接方式与发现配置，统一维护工具来源、连接状态和启停状态。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">服务列表</div>
          <div className="toolbar-right">
            <Button type="primary" onClick={openCreate}>
              + 新建 MCP Server
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索名称或显示名称"
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
                      <th>显示名称</th>
                      <th>类型</th>
                      <th>工具数量</th>
                      <th>连接状态</th>
                      <th>启用状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((record) => (
                      <tr key={record.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{record.name}</div>
                          <div style={{ color: '#6b7280', fontSize: 12 }}>{record.description || '-'}</div>
                        </td>
                        <td>{record.display_name}</td>
                        <td>
                          <span className={`tag ${transportTagClass(record.transport_type)}`}>
                            {transportDisplayMap[String(record.transport_type)] || String(record.transport_type)}
                          </span>
                        </td>
                        <td>{record.tool_count ?? '-'}</td>
                        <td>{connectionTag(record.status)}</td>
                        <td>
                          <StatusTag enabled={record.enabled} />
                        </td>
                        <td>
                          <div className="actions">
                            <button type="button" style={actionButtonStyle} onClick={() => void openEdit(record)}>
                              配置
                            </button>
                            <button
                              type="button"
                              style={actionButtonStyle}
                              disabled={actionLoadingId === record.id}
                              onClick={() => void handleConnect(record.id)}
                            >
                              连接
                            </button>
                            <button
                              type="button"
                              style={actionButtonStyle}
                              disabled={actionLoadingId === record.id}
                              onClick={() => void handleDiscover(record.id)}
                            >
                              发现
                            </button>
                            <button type="button" style={actionButtonStyle} onClick={() => void handleToggle(record)}>
                              {record.enabled ? '禁用' : '启用'}
                            </button>
                            <Popconfirm title="确认删除该 MCP Server？" onConfirm={() => void handleDelete(record.id)}>
                              <button type="button" style={dangerButtonStyle}>
                                删除
                              </button>
                            </Popconfirm>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!list.length ? (
                      <tr>
                        <td colSpan={7}>
                          <div className="empty-state">
                            <div className="empty-state-icon">🔌</div>
                            <div className="empty-state-text">暂无 MCP Server</div>
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
        title={editingId === null ? '新建 MCP Server' : '编辑 MCP Server'}
        width={540}
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
        <Form<MCPServerFormValues>
          form={form}
          layout="vertical"
          initialValues={{ transport_type: 'STDIO', auto_connect: false, enabled: true, env_vars: '{}' }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入唯一标识" disabled={editingId !== null} />
          </Form.Item>
          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="请输入展示名称" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入描述" />
          </Form.Item>
          <Form.Item
            label="Transport 类型"
            name="transport_type"
            rules={[{ required: true, message: '请选择 transport 类型' }]}
          >
            <Select
              options={[
                { label: 'stdio', value: 'STDIO' },
                { label: 'sse/http', value: 'HTTP_SSE' },
              ]}
            />
          </Form.Item>
          {transportType === 'STDIO' ? (
            <Form.Item
              label="命令行"
              name="command"
              rules={[{ required: true, message: '请输入启动命令' }]}
            >
              <Input placeholder="例如 npx -y @modelcontextprotocol/server-filesystem" />
            </Form.Item>
          ) : (
            <Form.Item
              label="URL"
              name="endpoint_url"
              rules={[{ required: true, message: '请输入服务地址' }]}
            >
              <Input placeholder="https://example.com/sse" />
            </Form.Item>
          )}
          <Form.Item
            label="环境变量(JSON)"
            name="env_vars"
            rules={[
              {
                validator: async (_, value?: string) => {
                  if (!value) return
                  try {
                    JSON.parse(value)
                  } catch {
                    throw new Error('请输入合法的 JSON')
                  }
                },
              },
            ]}
          >
            <Input.TextArea className="mono-textarea" rows={6} placeholder='例如 {"API_KEY":"xxx"}' />
          </Form.Item>
          <Form.Item label="自动连接" name="auto_connect" valuePropName="checked">
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>
          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
