import React, { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard, Mail, BarChart3, Settings, Shield,
  LogOut, Zap, Menu, X, ChevronRight, Bell
} from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/mailboxes', icon: Mail, label: 'Mailboxes' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const { user, company, logout, isSuperAdmin, accentColor } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/login') }

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-5 pb-0">
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shadow-orange-glow flex-shrink-0"
            style={{ background: `linear-gradient(135deg, ${accentColor}, ${accentColor}cc)` }}
          >
            <Zap className="w-4 h-4 text-white" fill="white" />
          </div>
          <div className="min-w-0">
            <p className="text-[9px] text-text-secondary font-semibold tracking-widest uppercase leading-none mb-0.5">
              {company?.is_neurogenix ? 'Neurogenix' : company?.name || 'WarmUp'}
            </p>
            <p className="text-sm font-bold text-white leading-none">WarmUp</p>
          </div>
        </div>

        {/* Company logo / avatar */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-bg-elevated border border-border mb-5">
          {company?.logo_url ? (
            <img src={`/api${company.logo_url}`} alt={company.name} className="w-8 h-8 rounded-lg object-contain" />
          ) : (
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
              style={{ backgroundColor: `${accentColor}33`, border: `1px solid ${accentColor}44` }}
            >
              {company?.name?.[0] || 'N'}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-white text-xs font-semibold truncate">{company?.name}</p>
            <p className="text-text-muted text-[10px] truncate">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        <p className="text-[10px] text-text-muted font-semibold uppercase tracking-widest px-3 py-2">Platform</p>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) => clsx('sidebar-link', isActive && 'active')}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}

        {isSuperAdmin && (
          <>
            <p className="text-[10px] text-text-muted font-semibold uppercase tracking-widest px-3 py-2 mt-3">
              Super Admin
            </p>
            <NavLink
              to="/admin"
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => clsx('sidebar-link', isActive && 'active')}
            >
              <Shield className="w-4 h-4 flex-shrink-0" />
              Manage Companies
            </NavLink>
          </>
        )}
      </nav>

      {/* Bottom */}
      <div className="p-3 space-y-1">
        <div className="p-3 rounded-xl bg-gradient-to-r from-orange/10 to-green/10 border border-orange/15 mb-2">
          <p className="text-[10px] text-text-secondary mb-1">Powered by</p>
          <p className="text-xs font-bold text-gradient-orange">Neurogenix AI</p>
        </div>
        <button
          id="sidebar-logout"
          onClick={handleLogout}
          className="sidebar-link w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen bg-bg-base overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-60 flex-col bg-bg-surface border-r border-border flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="relative w-60 bg-bg-surface border-r border-border flex flex-col">
            <button
              className="absolute top-4 right-4 text-text-secondary hover:text-white"
              onClick={() => setMobileOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-5 border-b border-border bg-bg-surface/80 backdrop-blur-sm flex-shrink-0">
          <button className="lg:hidden text-text-secondary hover:text-white" onClick={() => setMobileOpen(true)}>
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1 lg:flex-none" />
          <div className="flex items-center gap-3">
            <button className="relative text-text-secondary hover:text-white transition-colors">
              <Bell className="w-5 h-5" />
            </button>
            <div className="h-5 w-px bg-border" />
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                style={{ backgroundColor: `${accentColor}33` }}
              >
                {user?.full_name?.[0] || user?.email?.[0] || 'U'}
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-semibold text-white leading-none">{user?.full_name || user?.email}</p>
                <p className="text-[10px] text-text-muted capitalize">{user?.role?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-5 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
