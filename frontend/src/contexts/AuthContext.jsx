import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ng_user')) } catch { return null }
  })
  const [company, setCompany] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ng_company')) } catch { return null }
  })
  const [loading, setLoading] = useState(false)

  const login = async (email, password) => {
    setLoading(true)
    try {
      const { data } = await authApi.login(email, password)
      localStorage.setItem('ng_token', data.access_token)
      localStorage.setItem('ng_user', JSON.stringify(data.user))
      localStorage.setItem('ng_company', JSON.stringify(data.company))
      setUser(data.user)
      setCompany(data.company)
      return { success: true, user: data.user, company: data.company }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Login failed' }
    } finally {
      setLoading(false)
    }
  }

  const googleLogin = async (credential) => {
    setLoading(true)
    try {
      const { data } = await authApi.googleLogin(credential)
      localStorage.setItem('ng_token', data.access_token)
      localStorage.setItem('ng_user', JSON.stringify(data.user))
      localStorage.setItem('ng_company', JSON.stringify(data.company))
      setUser(data.user)
      setCompany(data.company)
      return { success: true, user: data.user, company: data.company }
    } catch (err) {
      return { success: false, error: err.response?.data?.detail || 'Google login failed' }
    } finally {
      setLoading(false)
    }
  }

  const logout = useCallback(() => {
    localStorage.removeItem('ng_token')
    localStorage.removeItem('ng_user')
    localStorage.removeItem('ng_company')
    setUser(null)
    setCompany(null)
  }, [])

  const isSuperAdmin = user?.role === 'super_admin'
  const isAdmin = user?.role === 'admin' || isSuperAdmin
  const accentColor = company?.accent_color || '#FF6B35'

  return (
    <AuthContext.Provider value={{ user, company, loading, login, googleLogin, logout, isSuperAdmin, isAdmin, accentColor }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
