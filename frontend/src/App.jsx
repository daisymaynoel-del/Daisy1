import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ContentFeed from './pages/ContentFeed'
import Approval from './pages/Approval'
import Analytics from './pages/Analytics'
import TrendTracker from './pages/TrendTracker'
import Suggestions from './pages/Suggestions'
import Reports from './pages/Reports'
import Upload from './pages/Upload'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import Finance from './pages/Finance'

function RequireAuth({ children }) {
  const authed = localStorage.getItem('eastend_auth') === 'true'
  return authed ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="upload" element={<Upload />} />
          <Route path="approval" element={<Approval />} />
          <Route path="content" element={<ContentFeed />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="trends" element={<TrendTracker />} />
          <Route path="suggestions" element={<Suggestions />} />
          <Route path="reports" element={<Reports />} />
          <Route path="finance" element={<Finance />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
