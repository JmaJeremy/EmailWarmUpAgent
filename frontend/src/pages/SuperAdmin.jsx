import React, { useEffect, useState } from 'react'
import { dashboardApi, companyApi } from '../api/client'
import {
  Shield, CheckCircle, XCircle, Clock, Mail, TrendingUp, Plus, X,
  Building, Inbox, ChevronDown, ChevronUp, User, Key, Zap, ArrowRight,
  BarChart2, Activity, RefreshCw, Lock
} from 'lucide-react'
import api from '../api/client'

// ─────────────────────────────────────────────────────────────────────────────
// CLIENT DETAIL SLIDE-OVER PANEL
// ─────────────────────────────────────────────────────────────────────────────
function ClientDetailPanel({ companyId, onClose, onRefresh }) {
  const [detail, setDetail]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [newPassword, setNewPassword] = useState('')
  const [pwLoading, setPwLoading]     = useState(false)
  const [pwMsg, setPwMsg]             = useState('')
  const [tab, setTab]           = useState('mailboxes') // 'mailboxes' | 'users' | 'settings'

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const { data } = await companyApi.getDetail(companyId)
        setDetail(data)
      } catch {} finally { setLoading(false) }
    }
    load()
  }, [companyId])

  const handleChangePassword = async () => {
    if (!newPassword.trim()) return
    setPwLoading(true); setPwMsg('')
    try {
      const { data } = await companyApi.changePassword(companyId, newPassword)
      setPwMsg(data.message)
      setNewPassword('')
    } catch (e) {
      setPwMsg(e.response?.data?.detail || 'Failed to update password')
    } finally { setPwLoading(false) }
  }

  const scoreColor = (score) => score >= 80 ? '#00D68F' : score >= 50 ? '#FF6B35' : '#EF4444'

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Slide-over panel */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-2xl bg-bg-card border-l border-border shadow-2xl flex flex-col animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border flex-shrink-0">
          {loading ? (
            <div className="skeleton h-6 w-40 rounded" />
          ) : (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm"
                style={{
                  backgroundColor: `${detail?.company.accent_color}33`,
                  border: `1px solid ${detail?.company.accent_color}55`
                }}>
                {detail?.company.name[0]}
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">{detail?.company.name}</h2>
                <p className="text-xs text-text-muted">{detail?.company.slug} · {detail?.company.status}</p>
              </div>
            </div>
          )}
          <button onClick={onClose} className="text-text-muted hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stats strip */}
        {!loading && detail && (
          <div className="grid grid-cols-4 divide-x divide-border border-b border-border flex-shrink-0">
            {[
              { label: 'Mailboxes', value: detail.stats.total_mailboxes },
              { label: 'Active', value: detail.stats.active_mailboxes, color: 'text-green' },
              { label: 'Avg Score', value: detail.stats.avg_score, color: `text-[${scoreColor(detail.stats.avg_score)}]` },
              { label: 'Emails Sent', value: detail.stats.total_sent },
            ].map(s => (
              <div key={s.label} className="p-4 text-center">
                <p className={`text-xl font-black text-white ${s.color || ''}`}>{s.value}</p>
                <p className="text-[10px] text-text-muted mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-border flex-shrink-0">
          {[
            { id: 'mailboxes', label: 'Mailboxes', icon: Mail },
            { id: 'users', label: 'Users & Access', icon: User },
            { id: 'settings', label: 'Admin Tools', icon: Key },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-all border-b-2 ${
                tab === t.id
                  ? 'border-orange text-orange'
                  : 'border-transparent text-text-secondary hover:text-white'
              }`}>
              <t.icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}
            </div>
          ) : (
            <>
              {/* ── MAILBOXES TAB ── */}
              {tab === 'mailboxes' && (
                <div className="space-y-3">
                  {detail.mailboxes.length === 0 ? (
                    <div className="text-center py-12 text-text-muted text-sm">
                      <Mail className="w-10 h-10 mx-auto mb-3 opacity-20" />
                      <p>No mailboxes yet.</p>
                      <p className="text-xs mt-1">Client needs to add mailboxes from their Mailboxes page.</p>
                    </div>
                  ) : (
                    detail.mailboxes.map(m => (
                      <div key={m.id} className="p-4 rounded-xl bg-bg-elevated border border-border">
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <p className="text-sm font-semibold text-white">{m.email_address}</p>
                            <p className="text-xs text-text-muted">Week {m.current_week} · {m.daily_limit} emails/day</p>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            m.warmup_status === 'active' ? 'bg-green/10 text-green border border-green/20' :
                            m.warmup_status === 'completed' ? 'bg-purple-400/10 text-purple-400 border border-purple-400/20' :
                            'bg-orange/10 text-orange border border-orange/20'
                          }`}>
                            {m.warmup_status}
                          </span>
                        </div>
                        {/* Score bar */}
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-bg-base rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{ width: `${m.warmup_score}%`, backgroundColor: scoreColor(m.warmup_score) }} />
                          </div>
                          <span className="text-xs font-bold" style={{ color: scoreColor(m.warmup_score) }}>
                            {Math.round(m.warmup_score)}
                          </span>
                        </div>
                        <div className="flex gap-4 mt-2">
                          {[
                            { label: 'Sent', value: m.total_sent },
                            { label: 'Opened', value: m.total_opened },
                            { label: 'Replied', value: m.total_replied },
                          ].map(s => (
                            <div key={s.label} className="text-center">
                              <p className="text-sm font-bold text-white">{s.value}</p>
                              <p className="text-[10px] text-text-muted">{s.label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ── USERS TAB ── */}
              {tab === 'users' && (
                <div className="space-y-3">
                  {detail.users.map(u => (
                    <div key={u.id} className="flex items-center gap-3 p-4 rounded-xl bg-bg-elevated border border-border">
                      <div className="w-9 h-9 rounded-full bg-orange/10 border border-orange/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-orange">{(u.full_name || u.email)[0].toUpperCase()}</span>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-white">{u.full_name || '—'}</p>
                        <p className="text-xs text-text-muted">{u.email}</p>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-bg-base border border-border text-text-secondary capitalize">
                        {u.role}
                      </span>
                      <span className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-green' : 'bg-red-400'}`} />
                    </div>
                  ))}
                </div>
              )}

              {/* ── ADMIN TOOLS TAB ── */}
              {tab === 'settings' && (
                <div className="space-y-6">
                  {/* Change Password */}
                  <div className="p-5 rounded-xl bg-bg-elevated border border-border">
                    <div className="flex items-center gap-2 mb-4">
                      <Lock className="w-4 h-4 text-orange" />
                      <h3 className="text-sm font-bold text-white">Reset Client Password</h3>
                    </div>
                    <p className="text-xs text-text-muted mb-3">
                      Set a new password for this client's admin account. Share it with them securely.
                    </p>
                    {pwMsg && (
                      <div className={`mb-3 px-3 py-2 rounded-lg text-xs ${
                        pwMsg.includes('fail') || pwMsg.includes('Failed')
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : 'bg-green/10 text-green border border-green/20'
                      }`}>{pwMsg}</div>
                    )}
                    <div className="flex gap-2">
                      <input
                        type="password"
                        placeholder="New password (min 6 chars)"
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                        className="input-field flex-1 text-sm"
                      />
                      <button
                        onClick={handleChangePassword}
                        disabled={pwLoading || newPassword.length < 6}
                        className="btn-primary text-sm px-4 py-2 flex-shrink-0"
                      >
                        {pwLoading ? 'Saving...' : 'Set Password'}
                      </button>
                    </div>
                  </div>

                  {/* Status control */}
                  <div className="p-5 rounded-xl bg-bg-elevated border border-border">
                    <div className="flex items-center gap-2 mb-4">
                      <Activity className="w-4 h-4 text-blue-accent" />
                      <h3 className="text-sm font-bold text-white">Account Status</h3>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={async () => { await companyApi.approve(companyId); onRefresh?.(); onClose() }}
                        className="flex-1 py-2 rounded-lg text-sm bg-green/10 border border-green/20 text-green hover:bg-green/20 transition-colors font-medium"
                      >
                        Activate Account
                      </button>
                      <button
                        onClick={async () => { if (!confirm('Suspend this company?')) return; await companyApi.suspend(companyId); onRefresh?.(); onClose() }}
                        className="flex-1 py-2 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-colors font-medium"
                      >
                        Suspend Account
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// ACCESS REQUESTS PANEL
// ─────────────────────────────────────────────────────────────────────────────
function AccessRequestsPanel() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading]   = useState(true)
  const [expanded, setExpanded] = useState(null)
  const [processing, setProcessing] = useState(null)
  const [filter, setFilter] = useState('pending') // 'pending' | 'history'

  const load = async () => {
    try { const { data } = await api.get('/access-requests'); setRequests(data) }
    catch {} finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const approve = async (id) => {
    setProcessing(id)
    try {
      const { data } = await api.post(`/access-requests/${id}/approve`)
      alert(`Account created!\n\nEmail: ${data.email}\nTemp Password: ${data.temp_password}\n\nShare these credentials securely.`)
      load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Approval failed')
    } finally { setProcessing(null) }
  }

  const dismiss = async (id) => {
    setProcessing(id)
    try { await api.post(`/access-requests/${id}/dismiss`); load() }
    catch {} finally { setProcessing(null) }
  }

  const pendingReqs = requests.filter(r => !r.is_reviewed)
  const historyReqs = requests.filter(r => r.is_reviewed)
  const displayReqs = filter === 'pending' ? pendingReqs : historyReqs

  return (
    <div className="glass-card rounded-2xl overflow-hidden shadow-2xl border border-border flex flex-col h-full max-h-[800px]">
      <div className="flex items-center justify-between p-5 border-b border-border bg-bg-elevated/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange/10 border border-orange/20 flex items-center justify-center">
            <Inbox className="w-4 h-4 text-orange" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Access Requests</h2>
            <p className="text-xs text-text-muted">From the "Request Access" form</p>
          </div>
        </div>
        <div className="flex bg-bg-base rounded-lg p-1 border border-border">
          <button onClick={() => setFilter('pending')}
            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-colors ${
              filter === 'pending' ? 'bg-orange text-white' : 'text-text-muted hover:text-white'
            }`}>
            Pending {pendingReqs.length > 0 && `(${pendingReqs.length})`}
          </button>
          <button onClick={() => setFilter('history')}
            className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-colors ${
              filter === 'history' ? 'bg-bg-elevated text-white border border-border' : 'text-text-muted hover:text-white'
            }`}>
            History
          </button>
        </div>
      </div>
      <div className="divide-y divide-border overflow-y-auto flex-1">
        {loading ? (
          <div className="p-6 space-y-3">{[...Array(2)].map((_, i) => <div key={i} className="skeleton h-14 rounded-xl" />)}</div>
        ) : displayReqs.length === 0 ? (
          <div className="p-10 text-center text-text-muted text-sm">
            <Inbox className="w-8 h-8 mx-auto mb-2 opacity-30" />
            {filter === 'pending' ? 'No pending requests.' : 'No request history.'}
          </div>
        ) : (
          displayReqs.map(req => (
            <div key={req.id} className={`p-4 ${!req.is_reviewed ? 'bg-orange/5 hover:bg-orange/10' : 'hover:bg-bg-elevated'} transition-colors`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-9 h-9 rounded-full bg-orange/10 border border-orange/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-xs font-bold text-orange">{req.full_name[0]}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-white">{req.full_name}</p>
                      <span className="text-xs text-text-muted">·</span>
                      <p className="text-xs text-text-muted">{req.company_name}</p>
                      {!req.is_reviewed && <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange/20 text-orange font-bold">NEW</span>}
                      {req.is_approved && <span className="text-[10px] px-1.5 py-0.5 rounded bg-green/20 text-green font-bold">APPROVED</span>}
                    </div>
                    <p className="text-xs text-text-secondary mt-0.5">{req.email}{req.phone ? ` · ${req.phone}` : ''}</p>
                    {req.message && expanded === req.id && (
                      <p className="text-xs text-text-secondary mt-2 p-3 rounded-lg bg-bg-base/50 border border-border italic">"{req.message}"</p>
                    )}
                    {req.message && (
                      <button onClick={() => setExpanded(expanded === req.id ? null : req.id)}
                        className="text-[10px] text-text-muted hover:text-white mt-1 flex items-center gap-1 transition-colors">
                        {expanded === req.id ? <><ChevronUp className="w-3 h-3" /> Hide</> : <><ChevronDown className="w-3 h-3" /> See message</>}
                      </button>
                    )}
                  </div>
                </div>
                {!req.is_approved && (
                  <div className="flex gap-2 flex-shrink-0">
                    <button onClick={() => dismiss(req.id)} disabled={processing === req.id}
                      className="px-2.5 py-1.5 rounded-lg text-xs bg-bg-elevated border border-border text-text-secondary hover:text-white transition-colors">
                      Dismiss
                    </button>
                    <button onClick={() => approve(req.id)} disabled={processing === req.id}
                      className="px-2.5 py-1.5 rounded-lg text-xs bg-green/10 border border-green/20 text-green hover:bg-green/20 font-semibold transition-colors">
                      {processing === req.id ? 'Creating...' : 'Approve'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPANY ROW (clickable)
// ─────────────────────────────────────────────────────────────────────────────
function StatusPill({ status }) {
  const map = {
    approved:  { cls: 'badge-active', label: 'Active' },
    pending:   { cls: 'badge-pending', label: 'Pending' },
    suspended: { cls: 'badge-error', label: 'Suspended' },
  }
  const s = map[status] || map.pending
  return <span className={s.cls}>{s.label}</span>
}

function CompanyRow({ company, onApprove, onSuspend, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 p-4 rounded-xl bg-bg-elevated border border-border hover:border-orange/30 hover:bg-orange/5 transition-all cursor-pointer group"
    >
      <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0 text-white"
        style={{ backgroundColor: `${company.accent_color}33`, border: `1px solid ${company.accent_color}44` }}>
        {company.name[0]}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-sm font-semibold text-white truncate">{company.name}</p>
          {company.is_neurogenix && <span className="text-[9px] px-1.5 py-0.5 rounded bg-orange/20 text-orange font-bold">YOU</span>}
        </div>
        <p className="text-xs text-text-muted">
          {company.mailboxes} mailboxes · {company.active_mailboxes} active · Score: {company.avg_score}
        </p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <StatusPill status={company.status} />
        {!company.is_neurogenix && (
          <div className="flex gap-1.5" onClick={e => e.stopPropagation()}>
            {company.status !== 'approved' && (
              <button onClick={() => onApprove(company.id)}
                className="p-1.5 rounded-lg bg-green/10 border border-green/20 text-green hover:bg-green/20 transition-colors" title="Approve">
                <CheckCircle className="w-4 h-4" />
              </button>
            )}
            {company.status !== 'suspended' && (
              <button onClick={() => onSuspend(company.id)}
                className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-colors" title="Suspend">
                <XCircle className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
        <ArrowRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// ADD CLIENT MODAL
// ─────────────────────────────────────────────────────────────────────────────
function AddClientModal({ onClose, onAdded }) {
  const [form, setForm] = useState({ name: '', email: '', password: '', full_name: '', accent_color: '#FF6B35' })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const presetColors = ['#FF6B35', '#00D68F', '#4D9CFF', '#A855F7', '#F59E0B', '#EC4899']

  const submit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true)
    try { await companyApi.create(form); onAdded() }
    catch (err) { setError(err.response?.data?.detail || 'Failed to create client') }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="glass-card rounded-2xl w-full max-w-md animate-slide-up">
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-lg font-bold text-white">Create Client Account</h2>
          <button onClick={onClose} className="text-text-muted hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Company Name *</label>
            <input required value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))}
              placeholder="Acme Corp" className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Admin Email *</label>
            <input required type="email" value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))}
              placeholder="admin@acme.com" className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Password *</label>
            <input required type="password" value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))}
              placeholder="Secure password" className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Brand Color</label>
            <div className="flex gap-2 flex-wrap">
              {presetColors.map(c => (
                <button key={c} type="button" onClick={() => setForm(f => ({...f, accent_color: c}))}
                  className="w-8 h-8 rounded-lg border-2 transition-all"
                  style={{ backgroundColor: c, borderColor: form.accent_color === c ? '#fff' : 'transparent' }} />
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Creating...' : 'Create Client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN SUPER ADMIN PAGE
// ─────────────────────────────────────────────────────────────────────────────
export default function SuperAdmin() {
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(true)
  const [showModal, setShowModal]   = useState(false)
  const [filter, setFilter]         = useState('all')
  const [selectedId, setSelectedId] = useState(null)  // which company to show in detail panel

  const load = async () => {
    setLoading(true)
    try { const { data: d } = await dashboardApi.superAdminOverview(); setData(d) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleApprove = async (id) => { await companyApi.approve(id); load() }
  const handleSuspend = async (id) => {
    if (!confirm('Suspend this company?')) return
    await companyApi.suspend(id); load()
  }

  const platform  = data?.platform || {}
  const companies = (data?.companies || []).filter(c =>
    filter === 'all' ? true : c.status === filter
  )

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-5 h-5 text-orange" />
            <h1 className="text-2xl font-black text-white">Super Admin</h1>
          </div>
          <p className="text-text-secondary text-sm">Neurogenix platform management</p>
        </div>
        <button id="add-client-btn" onClick={() => setShowModal(true)} className="btn-primary">
          <Plus className="w-4 h-4" /> Add Client
        </button>
      </div>

      {/* Platform stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total Companies', value: platform.total_companies || 0, icon: Building, color: 'text-white' },
          { label: 'Active', value: platform.active_companies || 0, icon: CheckCircle, color: 'text-green' },
          { label: 'Pending', value: platform.pending_companies || 0, icon: Clock, color: 'text-orange' },
          { label: 'Total Mailboxes', value: platform.total_mailboxes || 0, icon: Mail, color: 'text-blue-accent' },
          { label: 'Sent Today', value: platform.emails_sent_today || 0, icon: TrendingUp, color: 'text-purple-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass-card rounded-2xl p-4 border border-border">
            <Icon className={`w-4 h-4 ${color} mb-2`} />
            <p className={`text-2xl font-black ${color}`}>{value}</p>
            <p className="text-xs text-text-muted mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Access Requests */}
      <AccessRequestsPanel />

      {/* Pending banner */}
      {platform.pending_companies > 0 && (
        <div className="p-4 rounded-xl bg-orange/10 border border-orange/20 flex items-center gap-3">
          <Clock className="w-4 h-4 text-orange flex-shrink-0" />
          <p className="text-sm text-orange">
            <strong>{platform.pending_companies}</strong> company awaiting approval
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2">
        {['all', 'approved', 'pending', 'suspended'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              filter === f ? 'bg-orange text-white' : 'bg-bg-elevated border border-border text-text-secondary hover:text-white'
            }`}>
            {f}
          </button>
        ))}
      </div>

      {/* Companies list — click to open detail panel */}
      <div>
        <p className="text-xs text-text-muted mb-3">Click any row to view full client profile →</p>
        {loading ? (
          <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-16 rounded-xl" />)}</div>
        ) : (
          <div className="space-y-2">
            {companies.map(c => (
              <CompanyRow
                key={c.id}
                company={c}
                onApprove={handleApprove}
                onSuspend={handleSuspend}
                onClick={() => setSelectedId(c.id)}
              />
            ))}
            {companies.length === 0 && (
              <div className="glass-card rounded-2xl p-12 text-center">
                <Building className="w-10 h-10 text-text-muted mx-auto mb-3" />
                <p className="text-text-secondary text-sm">No companies found</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {showModal && (
        <AddClientModal onClose={() => setShowModal(false)} onAdded={() => { setShowModal(false); load() }} />
      )}

      {/* Client Detail Slide-Over */}
      {selectedId && (
        <ClientDetailPanel
          companyId={selectedId}
          onClose={() => setSelectedId(null)}
          onRefresh={load}
        />
      )}
    </div>
  )
}
