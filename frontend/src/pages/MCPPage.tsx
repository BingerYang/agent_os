import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import { mcpServerApi, normalizeListResponse, toolApi } from '../api'

type ToolProtocol = 'MCP' | 'HTTP' | 'BUILTIN'

interface ToolItem {
  id: number
  name: string
  display_name: string
  protocol: ToolProtocol
  endpoint_url?: string
  description?: string
  enabled: boolean
  mcp_server_id?: number | null
  mcp_server_name?: string
}

interface MCPServerOption {
  id: number
  name: string
  display_name?: string
}

interface ToolFormValues {
  name: string
  display_name: string
  protocol: ToolProtocol
  endpoint_url?: string
  mcp_server_id?: number
  description?: string
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

const protocolTagClass: Record<ToolProtocol, string> = {
  MCP: 'tag-blue',
  HTTP: 'tag-green',
  BUILTIN: 'tag-purple',
}

export default function MCPPage() {
  const [form] = Form.useForm<ToolFormValues>()
  const [tools, setTools] = useState<ToolItem[]>([])
  const [serverOptions, setServerOptions] = useState<MCPServerOption[]>([])
  const [loading, setLoading] = useState(false)
  const [serverLoading, setServerLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [selectedServerId, setSelectedServerId] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [modalOpen, setModalOpen] = useState(false)

  const loadServers = async () => {
    setServerLoading(true)
    try {
      const response = await mcpServerApi.list({ page: 1, page_size: 200 })
      const result = normalizeListResponse<MCPServerOption>(response)
      setServerOptions(result.items)
    } finally {
      setServerLoading(false)
    }
  }

  const loadTools = async () => {
    setLoading(true)
    try {
      const response = await toolApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
        mcp_server_id: selectedServerId,
      })
      const result = normalizeListResponse<ToolItem>(response)
      setTools(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadServers()
  }, [])

  useEffect(() => {
    void loadTools()
  }, [page, pageSize, keyword, selectedServerId])

  const handleCreate = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await toolApi.create({
        ...values,
        endpoint_url: values.endpoint_url?.trim() || undefined,
        description: values.description?.trim() || undefined,
        auth_type: 'NONE',
        auth_config: null,
        input_schema: {},
        output_schema: null,
        source_platform: 'local',
        tags: [],
        version: 'v1.0.0',
      })
      message.success('操作成功')
      setModalOpen(false)
      form.resetFields()
      await loadTools()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: ToolItem) => {
    await toolApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadTools()
  }

  const handleDelete = async (id: number) => {
    await toolApi.delete(id)
    message.success('操作成功')
    if (tools.length === 1 && page > 1) {
      setPage((current) => current - 1)
      return
    }
    await loadTools()
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
      <div className="page-title">工具库</div>
      <div className="page-desc">统一展示平台内所有工具能力，支持按 MCP Server 来源筛选，快速完成启停和新增管理。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">工具列表</div>
          <div className="toolbar-right">
            <Button
              type="primary"
              onClick={() => {
                form.resetFields()
                form.setFieldsValue({ protocol: 'MCP' })
                setModalOpen(true)
              }}
            >
              + 添加工具
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索工具名称"
                onSearch={(value) => {
                  setPage(1)
                  setKeyword(value)
                }}
              />
              <Select<number | undefined>
                allowClear
                className="toolbar-filter"
                placeholder="筛选来源 MCP Server"
                loading={serverLoading}
                value={selectedServerId}
                onChange={(value) => {
                  setPage(1)
                  setSelectedServerId(value)
                }}
                options={serverOptions.map((item) => ({
                  label: item.display_name || item.name,
                  value: item.id,
                }))}
              />
            </div>
          </div>

          {loading ? (
            <div className="table-loading">
              <Spin />
            </div>
          ) : tools.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🔧</div>
              <div className="empty-state-text">暂无工具</div>
            </div>
          ) : (
            <>
              <div className="tool-grid">
                {tools.map((item) => (
                  <div key={item.id} className="tool-card">
                    <div className="tool-card-header">
                      <div>
                        <div className="tool-card-title">{item.display_name || item.name}</div>
                        <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>{item.name}</div>
                      </div>
                      <span className={`tag ${protocolTagClass[item.protocol]}`}>{item.protocol}</span>
                    </div>
                    <div className="tool-card-desc ellipsis-2">{item.description || '暂无描述'}</div>
                    <div className="tool-card-meta">来源：{item.mcp_server_name || '内置工具'}</div>
                    <div className="tool-card-footer">
                      <Switch
                        checked={item.enabled}
                        checkedChildren="启用"
                        unCheckedChildren="禁用"
                        onChange={() => void handleToggle(item)}
                      />
                      <div className="actions">
                        <button type="button" style={actionButtonStyle}>
                          配置
                        </button>
                        <Popconfirm title="确认删除该工具？" onConfirm={() => void handleDelete(item.id)}>
                          <button type="button" style={dangerButtonStyle}>
                            删除
                          </button>
                        </Popconfirm>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="pagination-bar" style={{ paddingLeft: 0, paddingRight: 0, paddingBottom: 0 }}>
                <span>共 {total} 条记录</span>
                <Pagination {...paginationConfig} />
              </div>
            </>
          )}
        </div>
      </div>

      <Modal
        title="添加工具"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleCreate()}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        destroyOnClose
      >
        <Form<ToolFormValues> form={form} layout="vertical" initialValues={{ protocol: 'MCP' }}>
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入英文标识" />
          </Form.Item>
          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="请输入友好名称" />
          </Form.Item>
          <Form.Item
            label="协议"
            name="protocol"
            rules={[{ required: true, message: '请选择协议' }]}
          >
            <Select
              options={[
                { label: 'MCP', value: 'MCP' },
                { label: 'HTTP', value: 'HTTP' },
                { label: 'BUILTIN', value: 'BUILTIN' },
              ]}
            />
          </Form.Item>
          <Form.Item label="端点 URL" name="endpoint_url">
            <Input placeholder="请输入端点地址" />
          </Form.Item>
          <Form.Item label="来源 MCP Server" name="mcp_server_id">
            <Select
              allowClear
              placeholder="可选"
              options={serverOptions.map((item) => ({
                label: item.display_name || item.name,
                value: item.id,
              }))}
            />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入工具描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
