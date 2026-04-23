import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import ContentFeed from './pages/ContentFeed'
import Approval from './pages/Approval'
import Analytics from './pages/Analytics'
import TrendTracker from './pages/TrendTracker'
import Suggestions from './pages/Suggestions'
import Reports from './pages/Reports'
import Upload from './pages/Upload'
import Chat from './pages/Chat'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="content" element={<ContentFeed />} />
          <Route path="approval" element={<Approval />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="trends" element={<TrendTracker />} />
          <Route path="suggestions" element={<Suggestions />} />
          <Route path="reports" element={<Reports />} />
          <Route path="upload" element={<Upload />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
