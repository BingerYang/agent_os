import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Collapse, Input, message } from 'antd'
import { agentApi, normalizeListResponse } from '../api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type AgentType = 'SINGLE' | 'SUB' | 'ORCHESTRATOR'

interface PublishedAgentItem {
  id: number
  name: string
  agent_type: AgentType
  status: string
  enabled: boolean
  pipeline_uid?: string
  description?: string
}

interface MessageItem {
  id: string
  role: 'user' | 'agent' | 'error'
  content: string
  latency_ms?: number
  tools_called?: string[]
  streaming?: boolean
  thinking?: string
  thinking_streaming?: boolean
}

const agentTypeLabel: Record<AgentType, string> = {
  SINGLE: '单 Agent',
  SUB: '子 Agent',
  ORCHESTRATOR: '编排 Agent',
}

const agentTypeTagClass: Record<AgentType, string> = {
  SINGLE: 'tag-blue',
  SUB: 'tag-orange',
  ORCHESTRATOR: 'tag-red',
}

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''

const createSessionId = () => `sess-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

export default function ChatPage() {
  const [agents, setAgents] = useState<PublishedAgentItem[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(createSessionId)
  const [listLoading, setListLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const selectedAgent = useMemo(() => agents.find(a => a.id === selectedId) ?? null, [agents, selectedId])

  // 加载已发布 Agent
  const loadAgents = useCallback(async () => {
    setListLoading(true)
    try {
      const res = await agentApi.list({ page: 1, page_size: 500, status: 'published', enabled: true })
      const items = normalizeListResponse<PublishedAgentItem>(res).items
      const published = items.filter(a => a.status === 'published' && a.enabled && a.pipeline_uid)
      setAgents(published)
      setSelectedId(prev => {
        if (prev !== null && !published.find(a => a.id === prev)) {
          setMessages([])
          setSessionId(createSessionId())
          return published.length > 0 ? published[0].id : null
        }
        if (prev === null && published.length > 0) return published[0].id
        return prev
      })
    } finally {
      setListLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadAgents()
  }, [loadAgents])

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        void loadAgents()
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [loadAgents])

  // 切换 Agent 重置会话
  useEffect(() => {
    setMessages([])
    setInput('')
    setSessionId(createSessionId())
    abortRef.current?.abort()
  }, [selectedId])

  // 自动滚到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const appendToLastAgent = (id: string, chunk: string) => {
    setMessages(prev =>
      prev.map(m => m.id === id ? { ...m, content: m.content + chunk, streaming: true } : m)
    )
  }

  const finalizeAgent = (id: string, updates: Partial<MessageItem>) => {
    setMessages(prev =>
      prev.map(m => m.id === id ? { ...m, ...updates, streaming: false } : m)
    )
  }

  const handleSend = async () => {
    if (!selectedAgent?.pipeline_uid || !input.trim() || sending) return

    const query = input.trim()
    setInput('')
    setSending(true)

    const userMsgId = `u-${Date.now()}`
    const agentMsgId = `a-${Date.now()}`

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', content: query },
      { id: agentMsgId, role: 'agent', content: '', streaming: true },
    ])

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const resp = await fetch(`${BASE_URL}/api/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          pipeline_id: selectedAgent.pipeline_uid,
          stream: true,
          session_id: sessionId,
        }),
        signal: ctrl.signal,
      })

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`)
      }

      const reader = resp.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let buf = ''
      let finalAnswer = ''
      let latencyMs: number | undefined
      let toolsCalled: string[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const evt = JSON.parse(raw) as {
              type: string
              content?: string
              answer?: string
              latency_ms?: number
              tools_called?: string[]
            }
            if (evt.type === 'thinking') {
              const thinkingChunk = evt.content ?? ''
              if (thinkingChunk) {
                setMessages(prev =>
                  prev.map(m =>
                    m.id === agentMsgId
                      ? { ...m, thinking: (m.thinking ?? '') + thinkingChunk, thinking_streaming: true }
                      : m
                  )
                )
              }
            } else if (evt.type === 'answer') {
              const chunk = evt.content ?? ''
              finalAnswer += chunk
              appendToLastAgent(agentMsgId, chunk)
            } else if (evt.type === 'done') {
              latencyMs = evt.latency_ms
              toolsCalled = evt.tools_called ?? []
              finalizeAgent(agentMsgId, {
                content: evt.answer ?? finalAnswer ?? '（无回复）',
                latency_ms: latencyMs,
                tools_called: toolsCalled,
                thinking_streaming: false,
              })
            } else if (evt.type === 'error') {
              finalizeAgent(agentMsgId, {
                role: 'error',
                content: `错误：${(evt as Record<string, unknown>)['message'] ?? '未知错误'}`,
              })
            }
          } catch {
            // 忽略无法解析的行
          }
        }
      }

      // 如果没有收到 done 事件，用已积累内容收尾
      if (finalAnswer && !latencyMs) {
        finalizeAgent(agentMsgId, { content: finalAnswer })
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return
      finalizeAgent(agentMsgId, {
        role: 'error',
        content: '请求失败，请检查 Agent 配置和后端服务',
      })
    } finally {
      setSending(false)
    }
  }

  const canSend = Boolean(selectedAgent?.pipeline_uid) && input.trim().length > 0 && !sending

  return (
    <div style={{ height: 'calc(100vh - 56px - 48px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 className="page-title">对话演示</h1>
        <p className="page-desc" style={{ marginBottom: 0 }}>
          选择已发布的 Agent，通过其 Pipeline 直接发起对话，支持流式输出。
        </p>
      </div>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, minHeight: 0 }}>
        {/* 左侧 Agent 列表 */}
        <div className="page-card" style={{ overflow: 'hidden', marginBottom: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <div className="card-header-title">已发布 Agent</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {listLoading && <span style={{ fontSize: 12, color: '#9ca3af' }}>加载中…</span>}
              {!listLoading && (
                <Button size="small" onClick={() => void loadAgents()}>刷新</Button>
              )}
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {!listLoading && agents.length === 0 && (
              <div className="empty-state" style={{ padding: 32 }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>🤖</div>
                <div className="empty-state-text" style={{ textAlign: 'center', lineHeight: 1.8 }}>
                  暂无已发布 Agent<br />请在 Agent 管理页发布
                </div>
              </div>
            )}
            {agents.map(agent => {
              const active = agent.id === selectedId
              return (
                <div
                  key={agent.id}
                  className={`list-item${active ? ' active' : ''}`}
                  onClick={() => setSelectedId(agent.id)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="list-item-name">{agent.name}</div>
                  {agent.description && (
                    <div className="list-item-sub" style={{
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 1,
                      WebkitBoxOrient: 'vertical',
                    }}>{agent.description}</div>
                  )}
                  <div className="list-item-tags" style={{ marginTop: 6 }}>
                    <span className={`tag ${agentTypeTagClass[agent.agent_type]}`}>
                      {agentTypeLabel[agent.agent_type]}
                    </span>
                    {agent.pipeline_uid && (
                      <span className="tag tag-green">已就绪</span>
                    )}
                  </div>
                  {agent.pipeline_uid && active && (
                    <div style={{
                      marginTop: 8, padding: '6px 8px',
                      background: '#f0f7ff', borderRadius: 6,
                      fontSize: 10, fontFamily: 'monospace', color: '#6b7280',
                      wordBreak: 'break-all',
                    }}>
                      {agent.pipeline_uid}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* 右侧对话区 */}
        <div className="page-card" style={{ display: 'flex', flexDirection: 'column', marginBottom: 0, overflow: 'hidden' }}>
          {/* 头部 */}
          <div className="card-header" style={{ flexShrink: 0 }}>
            <div>
              <div className="card-header-title">
                {selectedAgent ? selectedAgent.name : '请从左侧选择 Agent'}
              </div>
              {selectedAgent?.pipeline_uid && (
                <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2, fontFamily: 'monospace' }}>
                  Pipeline: {selectedAgent.pipeline_uid}
                </div>
              )}
            </div>
            {selectedAgent?.pipeline_uid && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Button
                  size="small"
                  onClick={() => {
                    void navigator.clipboard.writeText(selectedAgent.pipeline_uid!).then(() => {
                      message.success('Pipeline ID 已复制')
                    })
                  }}
                >
                  复制 Pipeline ID
                </Button>
                <Button
                  size="small"
                  danger
                  onClick={() => { setMessages([]); setSessionId(createSessionId()) }}
                >
                  清空会话
                </Button>
              </div>
            )}
          </div>

          {/* 消息区 */}
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '20px',
              background: '#f8faff',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            {messages.length === 0 && (
              <div style={{
                flex: 1, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                color: '#9ca3af', gap: 12,
              }}>
                <div style={{ fontSize: 48 }}>💬</div>
                <div style={{ fontSize: 14 }}>
                  {selectedAgent ? '发送一条消息开始对话' : '请先从左侧选择一个 Agent'}
                </div>
              </div>
            )}

            {messages.map(msg => {
              if (msg.role === 'user') {
                return (
                  <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{
                      maxWidth: '70%', padding: '10px 14px',
                      background: '#2563eb', color: '#fff',
                      borderRadius: '12px 12px 2px 12px',
                      fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap',
                    }}>
                      {msg.content}
                    </div>
                  </div>
                )
              }

              const isError = msg.role === 'error'
              const isStreaming = msg.streaming && msg.content === ''

              return (
                <div key={msg.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{
                    width: 34, height: 34, borderRadius: 8, flexShrink: 0,
                    background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                    color: '#fff', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: 16,
                  }}>🤖</div>
                  <div style={{ maxWidth: '72%' }}>
                    {(msg.thinking || msg.thinking_streaming) && (
                      <Collapse
                        size="small"
                        style={{ marginBottom: 8 }}
                        items={[{
                          key: '1',
                          label: (
                            <span style={{ fontSize: 12, color: '#7c3aed', fontWeight: 500 }}>
                              💭 思考过程
                              {msg.thinking_streaming && (
                                <span style={{ marginLeft: 6, opacity: 0.6 }}>▌</span>
                              )}
                            </span>
                          ),
                          children: (
                            <div style={{
                              fontSize: 12,
                              color: '#6b7280',
                              whiteSpace: 'pre-wrap',
                              lineHeight: 1.6,
                              maxHeight: 240,
                              overflowY: 'auto',
                            }}>
                              {msg.thinking ?? ''}
                            </div>
                          ),
                        }]}
                      />
                    )}
                    <div style={{
                      padding: '10px 14px',
                      background: isError ? '#fee2e2' : '#fff',
                      border: `1px solid ${isError ? '#fca5a5' : '#e5e7eb'}`,
                      borderRadius: '2px 12px 12px 12px',
                      fontSize: 14, lineHeight: 1.6,
                      color: isError ? '#b91c1c' : '#111827',
                      minWidth: 60,
                    }}>
                      {isStreaming ? (
                        <span style={{ display: 'inline-flex', gap: 3 }}>
                          <span style={{ animation: 'blink 1s infinite' }}>●</span>
                          <span style={{ animation: 'blink 1s infinite 0.2s' }}>●</span>
                          <span style={{ animation: 'blink 1s infinite 0.4s' }}>●</span>
                        </span>
                      ) : isError ? (
                        <>
                          {msg.content}
                          {msg.streaming && <span style={{ opacity: 0.5 }}>▌</span>}
                        </>
                      ) : (
                        <>
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({ children }) => <p style={{ margin: '0 0 8px', lineHeight: 1.7 }}>{children}</p>,
                              pre: ({ children }) => (
                                <pre style={{
                                  background: '#1e293b',
                                  color: '#e2e8f0',
                                  padding: '12px 16px',
                                  borderRadius: 8,
                                  overflowX: 'auto',
                                  fontSize: 13,
                                  lineHeight: 1.6,
                                  margin: '8px 0',
                                }}>{children}</pre>
                              ),
                              code: ({ children, className }) => (
                                <code
                                  className={className}
                                  style={className ? {} : {
                                    background: '#f3f4f6',
                                    padding: '1px 5px',
                                    borderRadius: 4,
                                    fontSize: 13,
                                    fontFamily: 'ui-monospace, monospace',
                                  }}
                                >{children}</code>
                              ),
                              ul: ({ children }) => <ul style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ul>,
                              ol: ({ children }) => <ol style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ol>,
                              li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
                              blockquote: ({ children }) => (
                                <blockquote style={{
                                  borderLeft: '3px solid #d1d5db',
                                  paddingLeft: 12,
                                  margin: '8px 0',
                                  color: '#6b7280',
                                }}>{children}</blockquote>
                              ),
                              h1: ({ children }) => <h1 style={{ fontSize: 18, fontWeight: 700, margin: '12px 0 6px' }}>{children}</h1>,
                              h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: '10px 0 5px' }}>{children}</h2>,
                              h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '8px 0 4px' }}>{children}</h3>,
                              table: ({ children }) => (
                                <table style={{ borderCollapse: 'collapse', width: '100%', margin: '8px 0', fontSize: 13 }}>{children}</table>
                              ),
                              th: ({ children }) => (
                                <th style={{ border: '1px solid #e5e7eb', padding: '6px 10px', background: '#f9fafb', fontWeight: 600, textAlign: 'left' }}>{children}</th>
                              ),
                              td: ({ children }) => (
                                <td style={{ border: '1px solid #e5e7eb', padding: '6px 10px' }}>{children}</td>
                              ),
                              a: ({ href, children }) => (
                                <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>{children}</a>
                              ),
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                          {msg.streaming && <span style={{ opacity: 0.5 }}>▌</span>}
                        </>
                      )}
                    </div>
                    {/* 工具调用 + 耗时 */}
                    {(msg.tools_called?.length || typeof msg.latency_ms === 'number') && (
                      <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        {msg.tools_called?.map(t => (
                          <span key={t} className="tag tag-blue" style={{ fontSize: 10 }}>🔧 {t}</span>
                        ))}
                        {typeof msg.latency_ms === 'number' && (
                          <span style={{ fontSize: 11, color: '#9ca3af' }}>耗时 {msg.latency_ms}ms</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* 输入栏 */}
          <div style={{
            padding: '14px 20px',
            borderTop: '1px solid #e5e7eb',
            background: '#fff',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <Input.TextArea
                value={input}
                autoSize={{ minRows: 1, maxRows: 5 }}
                placeholder={
                  !selectedAgent
                    ? '请先从左侧选择已发布 Agent'
                    : !selectedAgent.pipeline_uid
                    ? '该 Agent 尚未生成 Pipeline ID，请重新发布'
                    : '输入消息… Enter 发送 / Shift+Enter 换行'
                }
                disabled={!selectedAgent?.pipeline_uid || sending}
                onChange={e => setInput(e.target.value)}
                onPressEnter={e => {
                  if (!e.shiftKey) {
                    e.preventDefault()
                    void handleSend()
                  }
                }}
                style={{ flex: 1, resize: 'none' }}
              />
              <Button
                type="primary"
                loading={sending}
                disabled={!canSend}
                onClick={() => void handleSend()}
                style={{ height: 36 }}
              >
                发送
              </Button>
            </div>
            {selectedAgent && !selectedAgent.pipeline_uid && (
              <div style={{ marginTop: 6, fontSize: 12, color: '#f59e0b' }}>
                ⚠️ 该 Agent 未找到 Pipeline ID，请在 Agent 管理页重新发布
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
      `}</style>
    </div>
  )
}
