import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Mailboxes from './pages/Mailboxes'
import WarmupStats from './pages/WarmupStats'
import SuperAdmin from './pages/SuperAdmin'
import Settings from './pages/Settings'

// Set your Google Client ID in frontend/.env as VITE_GOOGLE_CLIENT_ID=...
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

function ProtectedRoute({ children, requireSuperAdmin = false }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (requireSuperAdmin && user.role !== 'super_admin') return <Navigate to="/dashboard" replace />
  return children
}

function PublicRoute({ children }) {
  const { user } = useAuth()
  if (user) return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="mailboxes" element={<Mailboxes />} />
              <Route path="warmup/:mailboxId" element={<WarmupStats />} />
              <Route path="settings" element={<Settings />} />
              <Route path="admin" element={
                <ProtectedRoute requireSuperAdmin><SuperAdmin /></ProtectedRoute>
              } />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </GoogleOAuthProvider>
  )
}
