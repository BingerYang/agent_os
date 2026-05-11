import { useEffect, useState } from 'react'
import {
  Button,
  Form,
  Input,
  Modal,
  Pagination,
  Popconfirm,
  Select,
  Spin,
  Switch,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { PaginationProps } from 'antd'
import { mcpServerApi, normalizeListResponse, toolApi } from '../api'

type ToolProtocol = 'MCP' | 'HTTP' | 'BUILTIN'
type AuthType = 'NONE' | 'API_KEY' | 'BEARER_TOKEN' | 'JWT_BEARER' | 'BASIC_AUTH' | 'OAUTH2'

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
  description?: string
  endpoint_url?: string
  input_schema?: string
  auth_type: AuthType
  auth_key_name?: string
  auth_key_value?: string
  auth_key_location?: 'header' | 'query'
  auth_token?: string
  auth_username?: string
  auth_password?: string
  auth_access_token?: string
  auth_token_type?: string
  headers?: string
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

function buildToolAuthConfig(values: ToolFormValues): Record<string, unknown> | null {
  switch (values.auth_type) {
    case 'API_KEY':
      return {
        key_name: values.auth_key_name || 'X-API-Key',
        key_value: values.auth_key_value || '',
        key_location: values.auth_key_location || 'header',
      }
    case 'BEARER_TOKEN':
    case 'JWT_BEARER':
      return { token: values.auth_token || '' }
    case 'BASIC_AUTH':
      return { username: values.auth_username || '', password: values.auth_password || '' }
    case 'OAUTH2':
      return {
        access_token: values.auth_access_token || '',
        token_type: values.auth_token_type || 'bearer',
      }
    default:
      return null
  }
}

const protocolTagClass: Record<ToolProtocol, string> = {
  MCP: 'tag-blue',
  HTTP: 'tag-green',
  BUILTIN: 'tag-purple',
}

const protocolSourceLabel: Record<ToolProtocol, string> = {
  MCP: 'MCP',
  HTTP: 'HTTP 接口',
  BUILTIN: '内置',
}

const jsonValidator = async (_: unknown, value?: string) => {
  if (!value || value.trim() === '' || value.trim() === '{}') return
  try {
    JSON.parse(value)
  } catch {
    throw new Error('请输入合法的 JSON')
  }
}

export default function MCPPage() {
  const [form] = Form.useForm<ToolFormValues>()
  const protocol = Form.useWatch('protocol', form)
  const authType = Form.useWatch('auth_type', form)
  const [tools, setTools] = useState<ToolItem[]>([])
  const [serverOptions, setServerOptions] = useState<MCPServerOption[]>([])
  const [loading, setLoading] = useState(false)
  const [serverLoading, setServerLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [selectedServerId, setSelectedServerId] = useState<number | undefined>(undefined)
  const [enabledFilter, setEnabledFilter] = useState<'enabled' | 'disabled' | undefined>(undefined)
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
        enabled: enabledFilter === undefined ? undefined : enabledFilter === 'enabled',
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
  }, [page, pageSize, keyword, selectedServerId, enabledFilter])

  const handleCreate = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      const {
        auth_key_name,
        auth_key_value,
        auth_key_location,
        auth_token,
        auth_username,
        auth_password,
        auth_access_token,
        auth_token_type,
        ...restValues
      } = values
      const payload = {
        ...restValues,
        endpoint_url: values.protocol === 'HTTP' ? values.endpoint_url?.trim() || undefined : undefined,
        input_schema:
          values.protocol === 'HTTP' && values.input_schema
            ? (() => {
                try {
                  return JSON.parse(values.input_schema)
                } catch {
                  return {}
                }
              })()
            : {},
        auth_type: values.auth_type || 'NONE',
        auth_config: buildToolAuthConfig(values),
        headers: values.headers && values.headers.trim() !== '{}' ? JSON.parse(values.headers) : null,
        output_schema: null,
        source_platform: 'local',
        tags: [],
        version: 'v1.0.0',
      }

      await toolApi.create(payload)
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
      <div className="page-title">工具管理</div>
      <div className="page-desc">
        管理平台中的工具定义与接入方式，支持按 MCP Server、状态进行筛选，统一维护工具来源、认证方式与启停状态。
      </div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">工具列表</div>
          <div className="toolbar-right">
            <Button
              type="primary"
              onClick={() => {
                form.resetFields()
                form.setFieldsValue({ protocol: 'HTTP', auth_type: 'NONE', headers: '{}' })
                setModalOpen(true)
              }}
            >
              + 新建工具
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
                placeholder="筛选 MCP Server"
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
              <Select<'enabled' | 'disabled' | undefined>
                allowClear
                className="toolbar-filter"
                placeholder="筛选状态"
                value={enabledFilter}
                onChange={(value) => {
                  setPage(1)
                  setEnabledFilter(value)
                }}
                options={[
                  { label: '已启用', value: 'enabled' },
                  { label: '已禁用', value: 'disabled' },
                ]}
              />
            </div>
          </div>

          {loading ? (
            <div className="table-loading">
              <Spin />
            </div>
          ) : tools.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">暂无</div>
              <div className="empty-state-text">暂无工具</div>
            </div>
          ) : (
            <>
              <div className="tool-grid">
                {tools.map((item) => (
                  <div key={item.id} className="tool-card">
                    <div className="tool-card-header" style={{ alignItems: 'flex-start', gap: 12 }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <Typography.Text
                          style={{ display: 'block', fontSize: 15, fontWeight: 600 }}
                          ellipsis={{ tooltip: item.display_name || item.name }}
                          copyable={{ text: item.display_name || item.name }}
                        >
                          {item.display_name || item.name}
                        </Typography.Text>
                        <Typography.Text
                          style={{ display: 'block', color: '#9ca3af', fontSize: 12, marginTop: 4 }}
                          ellipsis={{ tooltip: item.name }}
                          copyable={{ text: item.name }}
                        >
                          {item.name}
                        </Typography.Text>
                      </div>
                      <span className={`tag ${protocolTagClass[item.protocol]}`}>
                        {item.protocol}
                      </span>
                    </div>
                    <div style={{ marginTop: 10, minHeight: 44 }}>
                      <Typography.Paragraph
                        type="secondary"
                        style={{ fontSize: 13, marginBottom: 0 }}
                        ellipsis={{ rows: 2 }}
                        copyable={item.description ? { text: item.description } : false}
                      >
                        {item.description || '暂无描述'}
                      </Typography.Paragraph>
                    </div>
                    <div className="tool-card-meta" style={{ marginTop: 12 }}>
                      <span>来源:</span>
                      <span style={{ marginLeft: 4 }}>{protocolSourceLabel[item.protocol]}</span>
                      {item.mcp_server_name ? (
                        <Tooltip title={item.mcp_server_name}>
                          <Typography.Text
                            style={{ color: '#2563eb', marginLeft: 8 }}
                            ellipsis={{ tooltip: item.mcp_server_name }}
                            copyable={{ text: item.mcp_server_name }}
                          >
                            {item.mcp_server_name}
                          </Typography.Text>
                        </Tooltip>
                      ) : null}
                    </div>
                    <div className="tool-card-footer">
                      <Switch
                        checked={item.enabled}
                        checkedChildren="已启用"
                        unCheckedChildren="已禁用"
                        onChange={() => void handleToggle(item)}
                      />
                      <div className="actions">
                        <button type="button" style={actionButtonStyle}>
                          配置
                        </button>
                        {item.protocol !== 'BUILTIN' ? (
                          <Popconfirm title="确认删除该工具吗？" onConfirm={() => void handleDelete(item.id)}>
                            <button type="button" style={dangerButtonStyle}>
                              删除
                            </button>
                          </Popconfirm>
                        ) : null}
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
        title="新建工具"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleCreate()}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
        destroyOnClose
      >
        <Form<ToolFormValues>
          form={form}
          layout="vertical"
          initialValues={{ protocol: 'HTTP', auth_type: 'NONE', headers: '{}' }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入唯一标识" />
          </Form.Item>
          <Form.Item
            label="显示名称"
            name="display_name"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="请输入展示名称" />
          </Form.Item>
          <Form.Item label="协议类型" name="protocol" rules={[{ required: true, message: '请选择协议类型' }]}>
            <Select
              options={[
                { label: 'MCP', value: 'MCP', disabled: true },
                { label: 'HTTP', value: 'HTTP' },
                { label: 'BUILTIN', value: 'BUILTIN', disabled: true },
              ]}
            />
          </Form.Item>
          {protocol === 'HTTP' ? (
            <>
              <Form.Item
                label="服务地址 URL"
                name="endpoint_url"
                rules={[{ required: true, message: '请输入服务地址' }]}
              >
                <Input placeholder="https://example.com/tool" />
              </Form.Item>
              <Form.Item label="Input Schema (JSON)" name="input_schema" rules={[{ validator: jsonValidator }]}>
                <Input.TextArea className="mono-textarea" rows={6} placeholder='{"type":"object","properties":{}}' />
              </Form.Item>
              <Form.Item label="认证方式" name="auth_type" initialValue="NONE">
                <Select
                  options={[
                    { label: '无认证', value: 'NONE' },
                    { label: 'API Key', value: 'API_KEY' },
                    { label: 'Bearer Token', value: 'BEARER_TOKEN' },
                    { label: 'JWT Bearer', value: 'JWT_BEARER' },
                    { label: 'Basic Auth', value: 'BASIC_AUTH' },
                    { label: 'OAuth 2.0', value: 'OAUTH2' },
                  ]}
                />
              </Form.Item>
              {(authType === 'BEARER_TOKEN' || authType === 'JWT_BEARER') && (
                <Form.Item label="Token" name="auth_token" rules={[{ required: true, message: '请输入 Token' }]}>
                  <Input.Password placeholder="请输入 Bearer Token" />
                </Form.Item>
              )}
              {authType === 'API_KEY' && (
                <>
                  <Form.Item label="Key 名称" name="auth_key_name" initialValue="X-API-Key">
                    <Input placeholder="X-API-Key" />
                  </Form.Item>
                  <Form.Item label="Key 值" name="auth_key_value" rules={[{ required: true, message: '请输入 Key 值' }]}>
                    <Input.Password placeholder="请输入 API Key" />
                  </Form.Item>
                  <Form.Item label="传入位置" name="auth_key_location" initialValue="header">
                    <Select
                      options={[
                        { label: 'Header', value: 'header' },
                        { label: 'Query 参数', value: 'query' },
                      ]}
                    />
                  </Form.Item>
                </>
              )}
              {authType === 'BASIC_AUTH' && (
                <>
                  <Form.Item label="用户名" name="auth_username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input placeholder="请输入用户名" />
                  </Form.Item>
                  <Form.Item label="密码" name="auth_password" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password placeholder="请输入密码" />
                  </Form.Item>
                </>
              )}
              {authType === 'OAUTH2' && (
                <>
                  <Form.Item
                    label="Access Token"
                    name="auth_access_token"
                    rules={[{ required: true, message: '请输入 Access Token' }]}
                  >
                    <Input.Password placeholder="请输入 OAuth2 Access Token" />
                  </Form.Item>
                  <Form.Item label="Token 类型" name="auth_token_type" initialValue="bearer">
                    <Input placeholder="bearer" />
                  </Form.Item>
                </>
              )}
              <Form.Item label="自定义请求头 (JSON)" name="headers" rules={[{ validator: jsonValidator }]}>
                <Input.TextArea className="mono-textarea" rows={4} placeholder='{"X-Custom-Header":"value"}' />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="请输入工具描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
