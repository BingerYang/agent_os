import { Outlet, useLocation, useNavigate } from 'react-router-dom'

const navGroups = [
  {
    title: '能力管理',
    items: [
      { path: '/models', label: '模型配置', icon: '🧠' },
      { path: '/mcp-servers', label: 'MCP Server', icon: '🔌' },
      { path: '/mcp', label: '工具库', icon: '🔧' },
      { path: '/skills', label: '技能管理', icon: '⚡' },
    ],
  },
  {
    title: '编排运行',
    items: [
      { path: '/agents', label: 'Agent 管理', icon: '🤖' },
      { path: '/detection-rules', label: '检测规则', icon: '🛡️' },
      { path: '/chat', label: '对话演示', icon: '💬' },
    ],
  },
]

const pageNames: Record<string, string> = {
  '/models': '模型配置',
  '/mcp-servers': 'MCP Server',
  '/mcp': '工具库',
  '/skills': '技能管理',
  '/agents': 'Agent 管理',
  '/detection-rules': '检测规则',
  '/chat': '对话演示',
}

export default function AppLayout() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-logo">
          <div className="app-logo-icon">🤖</div>
          <div>
            <div className="app-logo-title">AI 调度平台</div>
            <div className="app-logo-subtitle">Agent OS</div>
          </div>
        </div>

        <nav className="app-nav">
          {navGroups.map((group) => (
            <div key={group.title}>
              <div className="app-nav-group-title">{group.title}</div>
              {group.items.map((item) => {
                const active = pathname === item.path
                return (
                  <div
                    key={item.path}
                    className={`app-nav-item${active ? ' active' : ''}`}
                    onClick={() => navigate(item.path)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        navigate(item.path)
                      }
                    }}
                  >
                    <span style={{ fontSize: 15 }}>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="app-sidebar-user">
          <div className="app-avatar">A</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Admin</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>超级管理员</div>
          </div>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-header">
          <div className="app-breadcrumb">
            控制台 / <strong>{pageNames[pathname] || ''}</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 20, cursor: 'pointer', color: '#6b7280' }}>🔔</span>
            <div className="app-avatar" style={{ cursor: 'pointer' }}>
              A
            </div>
          </div>
        </header>

        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
