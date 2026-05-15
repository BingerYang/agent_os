import { useEffect, useState } from 'react'
import { Button, DatePicker, Pagination, Select, Spin, Tag, message } from 'antd'
import type { PaginationProps } from 'antd'
import dayjs from 'dayjs'
import { detectionEventApi, normalizeListResponse } from '../api'

interface DetectionEvent {
  id: number
  agent_id: number
  rule_id: number | null
  session_id: string | null
  stage: string
  strategy_type: string
  action_taken: string
  hit_detail: Record<string, unknown> | null
  input_snapshot: string | null
  status: string
  reviewer_id: string | null
  reviewer_note: string | null
  reviewed_at: string | null
  created_at: string
}

interface Props {
  agentId?: number
}

const STRATEGY_LABELS: Record<string, string> = {
  rate_limit: '限流防刷',
  identity_verify: '身份校验',
  content_filter: '违规内容',
  prompt_injection: 'Prompt 注入',
  pii_desensitize: 'PII 前置脱敏',
  intent_compliance: '意图合规',
  rbac_check: 'RBAC 校验',
  business_rule: '业务硬规则',
  privacy_leak: '后置隐私防泄',
  result_validation: '结果校验',
  human_approval: '人机审批',
}

const ACTION_LABELS: Record<string, string> = {
  block: '拦截',
  rewrite: '改写',
  log_review: '记录 Review',
  retry: '重试',
  log_only: '仅记录',
  degrade: '降级',
  escalate: '转人工',
  alert: '告警',
}

const STATUS_COLOR: Record<string, string> = {
  LOGGED: 'default',
  PENDING_REVIEW: 'warning',
  REVIEWED: 'success',
  ESCALATED: 'error',
  RESOLVED: 'processing',
}

const actionButtonStyle: React.CSSProperties = {
  color: '#2563eb',
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  fontSize: 12,
  padding: '2px 6px',
}

export default function DetectionEventList({ agentId }: Props) {
  const [list, setList] = useState<DetectionEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [reviewing, setReviewing] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [filterStrategy, setFilterStrategy] = useState<string | undefined>()
  const [filterStatus, setFilterStatus] = useState<string | undefined>()
  const [filterStage, setFilterStage] = useState<string | undefined>()
  const [startTime, setStartTime] = useState<string | undefined>()
  const [endTime, setEndTime] = useState<string | undefined>()

  const loadList = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize }
      if (agentId) params.agent_id = agentId
      if (filterStrategy) params.strategy_type = filterStrategy
      if (filterStatus) params.status = filterStatus
      if (filterStage) params.stage = filterStage
      if (startTime) params.start_time = startTime
      if (endTime) params.end_time = endTime
      const resp = await detectionEventApi.list(params)
      const result = normalizeListResponse<DetectionEvent>(resp)
      setList(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadList()
  }, [page, pageSize, filterStrategy, filterStatus, filterStage, startTime, endTime, agentId])

  const handleReview = async (event: DetectionEvent) => {
    setReviewing(event.id)
    try {
      await detectionEventApi.review(event.id, { status: 'REVIEWED', reviewer_note: '手动标注已复核' })
      message.success('已标注复核')
      await loadList()
    } finally {
      setReviewing(null)
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
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <Select
          allowClear
          placeholder="策略类型"
          style={{ width: 140 }}
          onChange={setFilterStrategy}
          options={Object.entries(STRATEGY_LABELS).map(([v, l]) => ({ value: v, label: l }))}
        />
        <Select
          allowClear
          placeholder="处置动作"
          style={{ width: 120 }}
          onChange={(v: string | undefined) => {
            setFilterStrategy(undefined)
            void (v)
          }}
          options={Object.entries(ACTION_LABELS).map(([v, l]) => ({ value: v, label: l }))}
        />
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 120 }}
          onChange={setFilterStatus}
          options={[
            { value: 'LOGGED', label: '已记录' },
            { value: 'PENDING_REVIEW', label: '待复核' },
            { value: 'REVIEWED', label: '已复核' },
            { value: 'ESCALATED', label: '已升级' },
            { value: 'RESOLVED', label: '已解决' },
          ]}
        />
        <Select
          allowClear
          placeholder="阶段"
          style={{ width: 100 }}
          onChange={setFilterStage}
          options={[
            { value: 'PRE', label: '前置' },
            { value: 'POST', label: '后置' },
          ]}
        />
        <DatePicker
          placeholder="开始时间"
          onChange={(d) => setStartTime(d ? dayjs(d).toISOString() : undefined)}
        />
        <DatePicker
          placeholder="结束时间"
          onChange={(d) => setEndTime(d ? dayjs(d).toISOString() : undefined)}
        />
        <Button onClick={() => void loadList()}>刷新</Button>
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
                  <th>时间</th>
                  <th>阶段</th>
                  <th>策略</th>
                  <th>处置</th>
                  <th>命中详情</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {list.map((evt) => (
                  <tr key={evt.id}>
                    <td style={{ whiteSpace: 'nowrap', fontSize: 12 }}>
                      {new Date(evt.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td>
                      <Tag color={evt.stage === 'PRE' ? 'blue' : 'purple'}>{evt.stage}</Tag>
                    </td>
                    <td>{STRATEGY_LABELS[evt.strategy_type] ?? evt.strategy_type}</td>
                    <td>{ACTION_LABELS[evt.action_taken] ?? evt.action_taken}</td>
                    <td>
                      <div
                        style={{
                          maxWidth: 220,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: 12,
                          color: '#666',
                        }}
                        title={evt.hit_detail ? JSON.stringify(evt.hit_detail) : ''}
                      >
                        {evt.hit_detail ? JSON.stringify(evt.hit_detail) : '-'}
                      </div>
                    </td>
                    <td>
                      <Tag color={STATUS_COLOR[evt.status] ?? 'default'}>{evt.status}</Tag>
                    </td>
                    <td>
                      {(evt.status === 'PENDING_REVIEW' || evt.status === 'ESCALATED') && (
                        <button
                          type="button"
                          style={actionButtonStyle}
                          disabled={reviewing === evt.id}
                          onClick={() => void handleReview(evt)}
                        >
                          {reviewing === evt.id ? '处理中...' : '标注复核'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {!list.length && (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <div className="empty-state-text">暂无检测事件</div>
                      </div>
                    </td>
                  </tr>
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
  )
}
