import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import AgentPage from './pages/AgentPage'
import ChatPage from './pages/ChatPage'
import DetectionRulesPage from './pages/DetectionRulesPage'
import MCPPage from './pages/MCPPage'
import MCPServersPage from './pages/MCPServersPage'
import ModelPage from './pages/ModelPage'
import SkillPage from './pages/SkillPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/agents" replace />} />
        <Route path="models" element={<ModelPage />} />
        <Route path="mcp-servers" element={<MCPServersPage />} />
        <Route path="mcp" element={<MCPPage />} />
        <Route path="skills" element={<SkillPage />} />
        <Route path="agents" element={<AgentPage />} />
        <Route path="detection-rules" element={<DetectionRulesPage />} />
        <Route path="chat" element={<ChatPage />} />
      </Route>
    </Routes>
  )
}
