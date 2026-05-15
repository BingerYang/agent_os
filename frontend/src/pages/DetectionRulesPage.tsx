import { useEffect, useRef, useState } from 'react'
import {
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Pagination,
  Popconfirm,
  Select,
  Spin,
  Switch,
  Tabs,
  Tag,
  message,
} from 'antd'
import type { PaginationProps } from 'antd'
import StatusTag from '../components/StatusTag'
import DetectionStrategyForm from '../components/DetectionStrategyForm'
import DetectionEventList from '../components/DetectionEventList'
import { detectionRuleApi, normalizeDetailResponse, normalizeListResponse, policyAuditApi } from '../api'

type RuleStage = 'PRE' | 'POST'
type RuleType = 'keyword' | 'llm_judge'

interface RuleItem {
  id: number
  name: string
  stage: RuleStage
  rule_type: RuleType
  strategy_type: string
  action_type: string
  max_retry_count: number
  rule_content?: Record<string, unknown>
  reject_message?: string
  priority: number
  enabled: boolean
}

interface RuleFormValues {
  name: string
  stage: RuleStage
  rule_type: RuleType
  strategy_type: string
  action_type: string
  max_retry_count: number
  reject_message?: string
  priority: number
  enabled: boolean
}

interface AuditItem {
  id: number
  operator_id: string
  agent_id: number | null
  rule_id: number
  change_type: string
  before_value: unknown
  after_value: unknown
  created_at: string
}

const STRATEGY_LABELS: Record<string, string> = {
  rate_limit: 'P-01 限流防刷',
  identity_verify: 'P-02 身份校验',
  content_filter: 'P-03 违规内容拦截',
  prompt_injection: 'P-04 Prompt 注入防护',
  pii_desensitize: 'P-05 PII 前置脱敏',
  intent_compliance: 'P-06 意图合规',
  rbac_check: 'P-07 RBAC 校验',
  business_rule: 'P-08 业务硬规则',
  privacy_leak: 'A-01 后置隐私防泄密',
  result_validation: 'A-02 业务结果校验',
  human_approval: 'A-03 人机审批',
}

const ACTION_LABELS: Record<string, string> = {
  block: '拦截',
  rewrite: '改写',
  log_review: '记录 Review（可继续）',
  retry: '重试',
  log_only: '仅记录',
  degrade: '降级',
  escalate: '转人工',
  alert: '告警',
}

const actionButtonStyle: React.CSSProperties = {
  color: '#2563eb',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontSize: 12,
  padding: '2px 6px',
}

const dangerButtonStyle: React.CSSProperties = { ...actionButtonStyle, color: '#ef4444' }

// ── Rule list tab ──────────────────────────────────────────────────────────────

function RuleListTab() {
  const [form] = Form.useForm<RuleFormValues>()
  const [list, setList] = useState<RuleItem[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [keyword, setKeyword] = useState('')
  const [filterStage, setFilterStage] = useState<string | undefined>()
  const [filterStrategy, setFilterStrategy] = useState<string | undefined>()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [ruleConfig, setRuleConfig] = useState<Record<string, unknown>>({})
  const currentStrategyType = Form.useWatch('strategy_type', form)

  const loadList = async () => {
    setLoading(true)
    try {
      const resp = await detectionRuleApi.list({
        page,
        page_size: pageSize,
        keyword: keyword.trim() || undefined,
        stage: filterStage,
        strategy_type: filterStrategy,
      })
      const result = normalizeListResponse<RuleItem>(resp)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadList() }, [page, pageSize, keyword, filterStage, filterStrategy])

  const openCreate = () => {
    setEditingId(null)
    form.resetFields()
    setRuleConfig({})
    form.setFieldsValue({
      stage: 'PRE',
      rule_type: 'keyword',
      strategy_type: 'content_filter',
      action_type: 'block',
      max_retry_count: 3,
      priority: 100,
      enabled: true,
    })
    setDrawerOpen(true)
  }

  const openEdit = async (record: RuleItem) => {
    setEditingId(record.id)
    setDrawerOpen(true)
    form.resetFields()
    setRuleConfig({})
    const detail = normalizeDetailResponse<RuleItem>(await detectionRuleApi.get(record.id))
    setRuleConfig(detail.rule_content || {})
    form.setFieldsValue({
      name: detail.name,
      stage: detail.stage,
      rule_type: detail.rule_type,
      strategy_type: detail.strategy_type,
      action_type: detail.action_type,
      max_retry_count: detail.max_retry_count,
      reject_message: detail.reject_message,
      priority: detail.priority,
      enabled: detail.enabled,
    })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload = {
      name: values.name.trim(),
      stage: values.stage,
      rule_type: values.rule_type,
      strategy_type: values.strategy_type,
      action_type: values.action_type,
      max_retry_count: values.max_retry_count,
      rule_content: ruleConfig,
      reject_message: values.reject_message?.trim(),
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

  const handleToggle = async (record: RuleItem) => {
    await detectionRuleApi.toggle(record.id, !record.enabled)
    message.success('操作成功')
    await loadList()
  }

  const handleDelete = async (id: number) => {
    await detectionRuleApi.delete(id)
    message.success('已删除')
    if (list.length === 1 && page > 1) setPage((c) => c - 1)
    else await loadList()
  }

  const paginationConfig: PaginationProps = {
    current: page, pageSize, total,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50, 100],
    onChange: (p, ps) => { setPage(p); setPageSize(ps) },
  }

  return (
    <>
      <div className="card-header">
        <div className="card-header-title">规则列表</div>
        <Button type="primary" onClick={openCreate}>+ 新建规则</Button>
      </div>
      <div className="card-body">
        <div className="toolbar">
          <div className="toolbar-left" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Input.Search
              allowClear
              className="toolbar-search"
              placeholder="搜索检测规则"
              onSearch={(v) => { setPage(1); setKeyword(v) }}
            />
            <Select
              allowClear
              placeholder="阶段"
              style={{ width: 100 }}
              onChange={(v) => { setPage(1); setFilterStage(v) }}
              options={[{ value: 'PRE', label: '前置' }, { value: 'POST', label: '后置' }]}
            />
            <Select
              allowClear
              placeholder="策略类型"
              style={{ width: 160 }}
              onChange={(v) => { setPage(1); setFilterStrategy(v) }}
              options={Object.entries(STRATEGY_LABELS).map(([v, l]) => ({ value: v, label: l }))}
            />
          </div>
        </div>

        {loading ? (
          <div className="table-loading"><Spin /></div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>名称</th>
                    <th>阶段</th>
                    <th>策略类型</th>
                    <th>处置动作</th>
                    <th>优先级</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((record) => (
                    <tr key={record.id}>
                      <td style={{ fontWeight: 600 }}>{record.name}</td>
                      <td>
                        <Tag color={record.stage === 'PRE' ? 'blue' : 'purple'}>{record.stage}</Tag>
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {STRATEGY_LABELS[record.strategy_type] ?? record.strategy_type}
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {ACTION_LABELS[record.action_type] ?? record.action_type}
                      </td>
                      <td>{record.priority}</td>
                      <td><StatusTag enabled={record.enabled} /></td>
                      <td>
                        <div className="actions">
                          <button type="button" style={actionButtonStyle} onClick={() => void openEdit(record)}>配置</button>
                          <button type="button" style={actionButtonStyle} onClick={() => void handleToggle(record)}>
                            {record.enabled ? '禁用' : '启用'}
                          </button>
                          <Popconfirm title="确认删除该规则？" onConfirm={() => void handleDelete(record.id)}>
                            <button type="button" style={dangerButtonStyle}>删除</button>
                          </Popconfirm>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!list.length && (
                    <tr><td colSpan={7}>
                      <div className="empty-state">
                        <div className="empty-state-icon">🛡️</div>
                        <div className="empty-state-text">暂无检测规则</div>
                      </div>
                    </td></tr>
                  )}
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

      <Drawer
        title={editingId === null ? '新建检测规则' : '编辑检测规则'}
        width={600}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
        extra={
          <div className="drawer-footer">
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={saving} onClick={() => void handleSubmit()}>保存</Button>
          </div>
        }
      >
        <Form<RuleFormValues>
          form={form}
          layout="vertical"
          initialValues={{ stage: 'PRE', rule_type: 'keyword', strategy_type: 'content_filter', action_type: 'block', max_retry_count: 3, priority: 100, enabled: true }}
        >
          <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="规则名称" />
          </Form.Item>
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item label="检测阶段" name="stage" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select options={[{ value: 'PRE', label: '前置 (PRE)' }, { value: 'POST', label: '后置 (POST)' }]} />
            </Form.Item>
            <Form.Item label="规则类型" name="rule_type" style={{ flex: 1 }}>
              <Select options={[{ value: 'keyword', label: '关键词' }, { value: 'llm_judge', label: 'LLM 裁判' }]} />
            </Form.Item>
          </div>
          <Form.Item label="策略类型" name="strategy_type" rules={[{ required: true }]}>
            <Select
              options={Object.entries(STRATEGY_LABELS).map(([v, l]) => ({ value: v, label: l }))}
              onChange={() => setRuleConfig({})}
            />
          </Form.Item>
          {currentStrategyType && (
            <Form.Item label="策略配置">
              <DetectionStrategyForm
                strategyType={currentStrategyType}
                value={ruleConfig}
                onChange={setRuleConfig}
              />
            </Form.Item>
          )}
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item label="处置动作" name="action_type" style={{ flex: 1 }} rules={[{ required: true }]}>
              <Select options={Object.entries(ACTION_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
            </Form.Item>
            <Form.Item label="最大重试次数" name="max_retry_count" style={{ flex: 1 }}>
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>
          </div>
          <Form.Item label="拦截提示消息" name="reject_message">
            <Input placeholder="策略命中时返回给用户的提示" />
          </Form.Item>
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item label="优先级" name="priority" style={{ flex: 1 }}>
              <InputNumber min={1} max={999} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="启用状态" name="enabled" valuePropName="checked" style={{ flex: 1 }}>
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </div>
        </Form>
      </Drawer>
    </>
  )
}

// ── Policy audit tab ───────────────────────────────────────────────────────────

function PolicyAuditTab() {
  const [list, setList] = useState<AuditItem[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)

  const loadList = async () => {
    setLoading(true)
    try {
      const resp = await policyAuditApi.list({ page, page_size: pageSize })
      const result = normalizeListResponse<AuditItem>(resp)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadList() }, [page, pageSize])

  const paginationConfig: PaginationProps = {
    current: page, pageSize, total,
    showSizeChanger: true,
    pageSizeOptions: [10, 20, 50],
    onChange: (p, ps) => { setPage(p); setPageSize(ps) },
  }

  return (
    <>
      {loading ? (
        <div className="table-loading"><Spin /></div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>操作人</th>
                  <th>规则 ID</th>
                  <th>Agent ID</th>
                  <th>变更类型</th>
                  <th>变更后</th>
                </tr>
              </thead>
              <tbody>
                {list.map((item) => (
                  <tr key={item.id}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>
                      {new Date(item.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td>{item.operator_id}</td>
                    <td>{item.rule_id}</td>
                    <td>{item.agent_id ?? '-'}</td>
                    <td><Tag>{item.change_type}</Tag></td>
                    <td>
                      <div style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, color: '#666' }}>
                        {item.after_value ? JSON.stringify(item.after_value) : '-'}
                      </div>
                    </td>
                  </tr>
                ))}
                {!list.length && (
                  <tr><td colSpan={6}>
                    <div className="empty-state">
                      <div className="empty-state-icon">📝</div>
                      <div className="empty-state-text">暂无变更记录</div>
                    </div>
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="pagination-bar">
            <span>共 {total} 条记录</span>
            <Pagination {...paginationConfig} />
          </div>
        </>
      )}
    </>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function DetectionRulesPage() {
  return (
    <div>
      <div className="page-title">检测规则</div>
      <div className="page-desc">
        统一维护前后置检测规则，支持 11 种策略类型、8 种处置动作，以及审计日志查询。
      </div>

      <div className="page-card">
        <Tabs
          defaultActiveKey="rules"
          items={[
            {
              key: 'rules',
              label: '策略模板',
              children: <RuleListTab />,
            },
            {
              key: 'audit_events',
              label: '检测事件',
              children: (
                <div className="card-body">
                  <DetectionEventList />
                </div>
              ),
            },
            {
              key: 'config_audit',
              label: '配置变更审计',
              children: (
                <div className="card-body">
                  <PolicyAuditTab />
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}
