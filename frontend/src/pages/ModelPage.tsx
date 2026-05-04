import { useEffect, useState } from 'react'
import { Button, Drawer, Form, Input, InputNumber, Pagination, Popconfirm, Select, Spin, Switch, message } from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import { modelApi, normalizeDetailResponse, normalizeListResponse } from '../api'

interface ModelItem {
  id: number
  name: string
  supplier: string
  category: string
  model_id: string
  endpoint_url?: string
  api_key?: string
  api_version?: string
  description?: string
  enabled: boolean
}

interface ModelFormValues {
  name: string
  supplier: string
  category: string
  model_id: string
  endpoint_url?: string
  api_key: string
  api_version?: string
  description?: string
  max_context_length?: number
  max_output_tokens?: number
  enabled: boolean
}

const providerOptions = ['阿里云百炼', '硅基流动', 'OpenAI', 'Azure', '自定义']

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

const supplierText = (supplier?: string) => supplier || '-'

export default function ModelPage() {
  const [form] = Form.useForm<ModelFormValues>()
  const [list, setList] = useState<ModelItem[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [editingId, setEditingId] = useState<number | null>(null)

  const loadList = async () => {
    setLoading(true)
    try {
      const response = await modelApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
      })
      const result = normalizeListResponse<ModelItem>(response)
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
      supplier: 'OpenAI',
      category: '通用模型',
      enabled: true,
      api_key: '',
      api_version: '',
      endpoint_url: '',
    })
    setDrawerOpen(true)
  }

  const openEdit = async (record: ModelItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    const detail = normalizeDetailResponse<ModelItem>(await modelApi.get(record.id))
    form.setFieldsValue({
      name: detail.name,
      supplier: detail.supplier,
      category: detail.category,
      model_id: detail.model_id,
      endpoint_url: detail.endpoint_url,
      api_key: '',
      api_version: detail.api_version,
      description: detail.description,
      enabled: detail.enabled,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      ...values,
      endpoint_url: values.endpoint_url?.trim() || undefined,
      api_version: values.api_version?.trim() || undefined,
      description: values.description?.trim() || undefined,
    }
    setSaving(true)
    try {
      if (editingId === null) {
        await modelApi.create(payload)
      } else {
        const updatePayload = {
          ...payload,
          api_key: payload.api_key?.trim() ? payload.api_key : undefined,
        }
        await modelApi.update(editingId, updatePayload)
      }
      message.success('操作成功')
      setDrawerOpen(false)
      await loadList()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (record: ModelItem) => {
    await modelApi.update(record.id, { enabled: !record.enabled })
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await modelApi.delete(id)
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
      <div className="page-title">模型配置</div>
      <div className="page-desc">管理各类 LLM 接入配置，统一维护供应商、模型标识、Endpoint 与认证信息。</div>

      <div className="page-card">
        <div className="card-header">
          <div className="card-header-title">模型列表</div>
          <div className="toolbar-right">
            <Button type="primary" onClick={openCreate}>
              + 新建模型
            </Button>
          </div>
        </div>
        <div className="card-body">
          <div className="toolbar">
            <div className="toolbar-left">
              <Input.Search
                allowClear
                className="toolbar-search"
                placeholder="搜索名称、供应商或模型 ID"
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
                      <th>提供商</th>
                      <th>模型 ID</th>
                      <th>Base URL</th>
                      <th>最大上下文</th>
                      <th>最大输出</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((record) => (
                      <tr key={record.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{record.name}</div>
                          <div style={{ color: '#6b7280', fontSize: 12 }}>{record.category || '通用模型'}</div>
                        </td>
                        <td>{supplierText(record.supplier)}</td>
                        <td>{record.model_id}</td>
                        <td>{record.endpoint_url || '-'}</td>
                        <td>{'-'}</td>
                        <td>{'-'}</td>
                        <td>
                          <StatusTag enabled={record.enabled} />
                        </td>
                        <td>
                          <div className="actions">
                            <button type="button" style={actionButtonStyle} onClick={() => void openEdit(record)}>
                              编辑
                            </button>
                            <button type="button" style={actionButtonStyle} onClick={() => void handleToggle(record)}>
                              {record.enabled ? '禁用' : '启用'}
                            </button>
                            <Popconfirm title="确认删除该模型配置？" onConfirm={() => void handleDelete(record.id)}>
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
                        <td colSpan={8}>
                          <div className="empty-state">
                            <div className="empty-state-icon">🧠</div>
                            <div className="empty-state-text">暂无模型配置</div>
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
        title={editingId === null ? '新建模型' : '编辑模型'}
        width={520}
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
        <Form<ModelFormValues> form={form} layout="vertical" initialValues={{ enabled: true }}>
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="请输入模型名称" />
          </Form.Item>
          <Form.Item
            label="提供商"
            name="supplier"
            rules={[{ required: true, message: '请选择提供商' }]}
          >
            <Select
              options={providerOptions.map((item) => ({
                label: item,
                value: item,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="模型 ID"
            name="model_id"
            rules={[{ required: true, message: '请输入模型 ID' }]}
          >
            <Input placeholder="例如 gpt-4o-mini" disabled={editingId !== null} />
          </Form.Item>
          <Form.Item
            label="模型类别"
            name="category"
            rules={[{ required: true, message: '请输入模型类别' }]}
          >
            <Input placeholder="例如 通用模型 / 推理模型" />
          </Form.Item>
          <Form.Item label="Base URL" name="endpoint_url">
            <Input placeholder="请输入 API Base URL" />
          </Form.Item>
          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: editingId === null, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder={editingId === null ? '请输入 API Key' : '如需更新请重新输入 API Key'} />
          </Form.Item>
          <Form.Item label="API 版本" name="api_version">
            <Input placeholder="可选，例如 2024-10-01-preview" />
          </Form.Item>
          <Form.Item label="最大上下文">
            <InputNumber style={{ width: '100%' }} disabled placeholder="当前后端暂未提供该字段" />
          </Form.Item>
          <Form.Item label="最大输出">
            <InputNumber style={{ width: '100%' }} disabled placeholder="当前后端暂未提供该字段" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={3} placeholder="补充模型用途或接入说明" />
          </Form.Item>
          <Form.Item label="是否启用" name="enabled" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
