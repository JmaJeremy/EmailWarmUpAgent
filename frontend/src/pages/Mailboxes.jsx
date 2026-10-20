import React, { useEffect, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { mailboxApi, warmupApi } from '../api/client'
import {
  Plus, Mail, Play, Pause, Trash2, TestTube, ChevronDown, ChevronUp,
  Wifi, AlertCircle, CheckCircle, Clock, Zap, X, Eye, EyeOff, Upload
} from 'lucide-react'
import clsx from 'clsx'
import api from '../api/client'

const WEEK_LIMITS = { 1:3, 2:6, 3:12, 4:20, 5:30, 6:40, 7:50, 8:60 }

function StatusBadge({ status }) {
  const map = {
    active: { cls: 'badge-active', dot: 'bg-green', label: 'Active' },
    paused: { cls: 'badge-paused', dot: 'bg-yellow-400', label: 'Paused' },
    pending: { cls: 'badge-pending', dot: 'bg-blue-accent', label: 'Pending' },
    completed: { cls: 'badge-completed', dot: 'bg-purple-400', label: 'Completed' },
    error: { cls: 'badge-error', dot: 'bg-red-400', label: 'Error' },
  }
  const s = map[status] || map.pending
  return (
    <span className={s.cls}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} animate-pulse-slow`} />
      {s.label}
    </span>
  )
}

function ScoreBar({ score }) {
  const color = score >= 80 ? '#00D68F' : score >= 50 ? '#FF6B35' : '#EF4444'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-bg-base rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-bold" style={{ color }}>{Math.round(score)}</span>
    </div>
  )
}

function MailboxCard({ mailbox, onRefresh }) {
  const [loading, setLoading] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [editingLimit, setEditingLimit] = useState(false)
  const [newLimit, setNewLimit] = useState(mailbox.daily_limit || 3)

  const weekLimit = mailbox.daily_limit || 3
  const needsMicrosoftConnect = mailbox.auth_type === 'microsoft_graph' && !mailbox.oauth_connected
  const progressPct = Math.round((mailbox.current_week / 8) * 100)

  const handleStart = async () => {
    setLoading(true)
    try { await mailboxApi.startWarmup(mailbox.id); onRefresh() } finally { setLoading(false) }
  }
  const handlePause = async () => {
    setLoading(true)
    try { await mailboxApi.pauseWarmup(mailbox.id); onRefresh() } finally { setLoading(false) }
  }
  const handleDelete = async () => {
    if (!confirm(`Delete ${mailbox.email_address}? This cannot be undone.`)) return
    await mailboxApi.delete(mailbox.id)
    onRefresh()
  }
  const handleTest = async () => {
    setTesting(true); setTestResult(null)
    try {
      const { data } = await mailboxApi.testConnection(mailbox.id)
      setTestResult(data)
    } catch { setTestResult({ overall: false, smtp: { success: false, message: 'Request failed' }, imap: { success: false, message: 'Request failed' } }) }
    finally { setTesting(false) }
  }
  const handleSaveLimit = async () => {
    if (newLimit < 1) return alert('Limit must be at least 1')
    setLoading(true)
    try {
      await mailboxApi.update(mailbox.id, { daily_limit: newLimit })
      onRefresh()
    } catch (e) {
      alert('Failed to update limit')
    } finally {
      setLoading(false)
      setEditingLimit(false)
    }
  }

  return (
    <div className="glass-card rounded-2xl border border-border hover:border-white/10 transition-all duration-300 animate-fade-in">
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-orange/10 border border-orange/20 flex items-center justify-center flex-shrink-0">
              <Mail className="w-5 h-5 text-orange" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{mailbox.email_address}</p>
              <p className="text-xs text-text-muted truncate">{mailbox.display_name}</p>
            </div>
          </div>
          <StatusBadge status={mailbox.warmup_status} />
        </div>

        {/* Week progress & limit editing */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs text-text-secondary font-medium flex items-center gap-2">
              Week {mailbox.current_week}/8 —
              {editingLimit ? (
                <span className="flex items-center gap-1">
                  <input type="number" min="1" className="w-16 px-1.5 py-0.5 text-xs text-white bg-bg-base border border-orange rounded outline-none" value={newLimit} onChange={e => setNewLimit(Number(e.target.value))} autoFocus />
                  <button onClick={handleSaveLimit} className="text-green hover:underline">Save</button>
                  <button onClick={() => { setEditingLimit(false); setNewLimit(weekLimit) }} className="text-text-muted hover:text-white">Cancel</button>
                </span>
              ) : (
                <span className="text-white flex items-center gap-1.5 group cursor-pointer" onClick={() => setEditingLimit(true)}>
                  <span className="bg-bg-elevated px-1.5 py-0.5 rounded border border-border text-orange font-bold group-hover:border-orange/50 transition-colors">{weekLimit}</span> emails/day
                  <span className="text-[10px] text-text-muted group-hover:text-white underline hidden lg:inline">Edit</span>
                </span>
              )}
            </p>
            <p className="text-xs text-text-muted">{progressPct}%</p>
          </div>
          <div className="h-1.5 bg-bg-base rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-orange to-orange-dark transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Score */}
        <div className="mb-4">
          <p className="text-xs text-text-secondary mb-1.5">Warmup Score</p>
          <ScoreBar score={mailbox.warmup_score || 0} />
        </div>

        {/* Mini stats */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          {[
            { label: 'Sent', value: mailbox.total_sent || 0, color: 'text-orange' },
            { label: 'Opened', value: mailbox.total_opened || 0, color: 'text-green' },
            { label: 'Replied', value: mailbox.total_replied || 0, color: 'text-blue-accent' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-bg-elevated rounded-xl p-2.5 text-center border border-border">
              <p className={`text-base font-bold ${color}`}>{value}</p>
              <p className="text-[10px] text-text-muted">{label}</p>
            </div>
          ))}
        </div>

        {needsMicrosoftConnect && (
          <div className="mb-3 p-3 rounded-xl bg-orange/10 border border-orange/20 text-xs text-orange space-y-2">
            <p>Not connected yet — sign in with this Microsoft 365 account before starting warmup.</p>
            <ConnectMicrosoftButton mailboxId={mailbox.id} />
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          {mailbox.warmup_status === 'active' ? (
            <button id={`pause-${mailbox.id}`} onClick={handlePause} disabled={loading} className="btn-secondary flex-1 text-xs py-2">
              <Pause className="w-3.5 h-3.5" /> Pause
            </button>
          ) : mailbox.warmup_status !== 'completed' ? (
            <button id={`start-${mailbox.id}`} onClick={handleStart} disabled={loading || needsMicrosoftConnect} className="btn-primary flex-1 text-xs py-2">
              <Play className="w-3.5 h-3.5" /> Start Warmup
            </button>
          ) : (
            <span className="badge-completed flex-1 justify-center text-xs py-2">🎉 Complete</span>
          )}
          <button onClick={handleTest} disabled={testing} className="btn-secondary px-3 py-2 text-xs">
            <Wifi className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => setExpanded(e => !e)} className="btn-ghost px-3 py-2">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          <button onClick={handleDelete} className="text-red-400 hover:text-red-300 px-2 py-2 rounded-lg hover:bg-red-500/10 transition-colors">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`mt-3 p-3 rounded-xl border text-xs space-y-1 ${testResult.overall ? 'bg-green/10 border-green/20' : 'bg-red-500/10 border-red-500/20'}`}>
            <div className="flex items-center gap-2">
              {testResult.smtp?.success ? <CheckCircle className="w-3.5 h-3.5 text-green" /> : <AlertCircle className="w-3.5 h-3.5 text-red-400" />}
              <span className="text-text-secondary">Send:</span>
              <span className={testResult.smtp?.success ? 'text-green' : 'text-red-400'}>{testResult.smtp?.message}</span>
            </div>
            <div className="flex items-center gap-2">
              {testResult.imap?.success ? <CheckCircle className="w-3.5 h-3.5 text-green" /> : <AlertCircle className="w-3.5 h-3.5 text-red-400" />}
              <span className="text-text-secondary">Read:</span>
              <span className={testResult.imap?.success ? 'text-green' : 'text-red-400'}>{testResult.imap?.message}</span>
            </div>
          </div>
        )}

        {/* Expanded */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-border text-xs space-y-1.5">
            {mailbox.auth_type !== 'microsoft_graph' && (<>
              <div className="flex justify-between"><span className="text-text-muted">SMTP</span><span className="text-text-secondary">{mailbox.smtp_host}:{mailbox.smtp_port}</span></div>
              <div className="flex justify-between"><span className="text-text-muted">IMAP</span><span className="text-text-secondary">{mailbox.imap_host}:{mailbox.imap_port}</span></div>
            </>)}
            {/* Auth type badge */}
            <div className="flex justify-between items-center pt-1">
              <span className="text-text-muted">Send via</span>
              {mailbox.auth_type === 'gmail_api'
                ? <span className="px-2 py-0.5 rounded-full bg-green/10 border border-green/20 text-green text-[10px] font-bold">✅ Gmail API</span>
                : mailbox.auth_type === 'microsoft_graph'
                ? <span className="px-2 py-0.5 rounded-full bg-blue-accent/10 border border-blue-accent/20 text-blue-400 text-[10px] font-bold">{mailbox.oauth_connected ? '✅ Microsoft Graph' : 'Microsoft Graph (not connected)'}</span>
                : <span className="px-2 py-0.5 rounded-full bg-orange/10 border border-orange/20 text-orange text-[10px] font-bold">SMTP</span>
              }
            </div>
            {/* Reconnect Microsoft (e.g. after a password change or revoked consent) */}
            {mailbox.auth_type === 'microsoft_graph' && mailbox.oauth_connected && (
              <ConnectMicrosoftButton mailboxId={mailbox.id} label="Reconnect Microsoft account" />
            )}
            {/* Connect with Google — only offered for Gmail mailboxes not yet on the Gmail API */}
            {mailbox.auth_type === 'smtp' && mailbox.smtp_host === 'smtp.gmail.com' && (
              <button
                onClick={async () => {
                  try {
                    const { data } = await api.get(`/mailboxes/oauth/google-url?mailbox_id=${mailbox.id}`)
                    window.location.href = data.auth_url
                  } catch (e) {
                    alert(e.response?.data?.detail || 'Could not get Google auth URL. Check GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are set.')
                  }
                }}
                className="w-full mt-2 flex items-center justify-center gap-2 py-2 rounded-xl border border-white/10 bg-white text-gray-700 text-xs font-semibold hover:bg-gray-50 transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Connect with Google
              </button>
            )}
            <div className="flex justify-between"><span className="text-text-muted">Last warmup</span><span className="text-text-secondary">{mailbox.last_warmup_at ? new Date(mailbox.last_warmup_at).toLocaleDateString() : 'Never'}</span></div>
          </div>
        )}
      </div>
    </div>
  )
}

async function startMicrosoftConnect(mailboxId) {
  try {
    const { data } = await api.get(`/mailboxes/oauth/microsoft-url?mailbox_id=${mailboxId}`)
    window.location.href = data.auth_url
  } catch (e) {
    alert(e.response?.data?.detail || 'Could not get Microsoft sign-in URL.')
  }
}

function ConnectMicrosoftButton({ mailboxId, label = 'Connect with Microsoft' }) {
  return (
    <button
      onClick={() => startMicrosoftConnect(mailboxId)}
      className="w-full mt-2 flex items-center justify-center gap-2 py-2 rounded-xl border border-white/10 bg-white text-gray-700 text-xs font-semibold hover:bg-gray-50 transition-colors"
    >
      <svg width="14" height="14" viewBox="0 0 21 21"><rect x="1" y="1" width="9" height="9" fill="#F25022"/><rect x="11" y="1" width="9" height="9" fill="#7FBA00"/><rect x="1" y="11" width="9" height="9" fill="#00A4EF"/><rect x="11" y="11" width="9" height="9" fill="#FFB900"/></svg>
      {label}
    </button>
  )
}

function AddMailboxModal({ onClose, onAdded }) {
  const [mode, setMode] = useState('smtp') // smtp | microsoft_graph
  const [form, setForm] = useState({
    email_address: '', display_name: '',
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '', smtp_use_tls: true,
    imap_host: '', imap_port: 993, imap_user: '', imap_password: '', imap_use_ssl: true,
  })
  const [showPass, setShowPass] = useState({ smtp: false, imap: false })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Auto-fill common providers (all use app passwords / regular passwords over SMTP + IMAP)
  const presets = {
    Gmail:      { smtp_host: 'smtp.gmail.com',       smtp_port: 587, imap_host: 'imap.gmail.com',       imap_port: 993 },
    Purelymail: { smtp_host: 'smtp.purelymail.com',  smtp_port: 587, imap_host: 'imap.purelymail.com',  imap_port: 993 },
    Fastmail:   { smtp_host: 'smtp.fastmail.com',    smtp_port: 587, imap_host: 'imap.fastmail.com',    imap_port: 993 },
    Zoho:       { smtp_host: 'smtp.zoho.com',        smtp_port: 587, imap_host: 'imap.zoho.com',        imap_port: 993 },
    iCloud:     { smtp_host: 'smtp.mail.me.com',     smtp_port: 587, imap_host: 'imap.mail.me.com',     imap_port: 993 },
    Yahoo:      { smtp_host: 'smtp.mail.yahoo.com',  smtp_port: 587, imap_host: 'imap.mail.yahoo.com',  imap_port: 993 },
  }

  // Port 465 = implicit TLS; anything else = STARTTLS
  const set = (k, v) => setForm(f => ({ ...f, [k]: v, ...(k === 'smtp_port' ? { smtp_use_tls: Number(v) !== 465 } : {}) }))
  const applyPreset = (p) => setForm(f => ({ ...f, ...presets[p], smtp_use_tls: presets[p].smtp_port !== 465 }))
  // Most providers use the email address as the login — fill it in unless the user typed something else
  const setEmail = (v) => setForm(f => ({
    ...f, email_address: v,
    smtp_user: !f.smtp_user || f.smtp_user === f.email_address ? v : f.smtp_user,
    imap_user: !f.imap_user || f.imap_user === f.email_address ? v : f.imap_user,
  }))

  const submit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      if (mode === 'microsoft_graph') {
        const { data } = await mailboxApi.add({
          email_address: form.email_address, display_name: form.display_name, auth_type: 'microsoft_graph',
        })
        await startMicrosoftConnect(data.mailbox.id)  // leaves the page for Microsoft sign-in
        return
      }
      await mailboxApi.add({ ...form, auth_type: 'smtp', smtp_port: Number(form.smtp_port), imap_port: Number(form.imap_port) })
      onAdded()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Failed to add mailbox')
    } finally { setLoading(false) }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm">
      <div className="min-h-full flex items-start justify-center p-4 pt-24 pb-16">
        <div className="glass-card rounded-2xl w-full max-w-3xl min-h-[600px] animate-slide-up">
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div>
              <h2 className="text-lg font-bold text-white">Add Mailbox</h2>
              <p className="text-xs text-text-secondary mt-0.5">
                {mode === 'microsoft_graph' ? 'Sign in with Microsoft 365 after adding' : 'Configure SMTP + IMAP credentials for warmup'}
              </p>
            </div>
            <button onClick={onClose} className="text-text-muted hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={submit} className="p-6 space-y-5">
            {error && (
              <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Connection type */}
            <div>
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Connection Type</p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'smtp', title: 'SMTP + IMAP', desc: 'Gmail (app password), Purelymail, Fastmail, Zoho, …' },
                  { id: 'microsoft_graph', title: 'Microsoft 365', desc: 'Exchange Online / Outlook — sign in with Microsoft' },
                ].map(o => (
                  <button key={o.id} type="button" onClick={() => setMode(o.id)}
                    className={clsx('p-3 rounded-xl border text-left transition-all',
                      mode === o.id ? 'border-orange bg-orange/10' : 'border-border bg-bg-elevated hover:border-orange/40')}>
                    <p className="text-sm font-semibold text-white">{o.title}</p>
                    <p className="text-[11px] text-text-muted mt-0.5">{o.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Quick presets */}
            {mode === 'smtp' && <div>
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Quick Presets</p>
              <div className="flex flex-wrap gap-2">
                {Object.keys(presets).map(p => (
                  <button key={p} type="button" onClick={() => applyPreset(p)}
                    className="px-3 py-1.5 rounded-lg bg-bg-elevated border border-border text-xs text-text-secondary hover:text-white hover:border-orange/40 transition-all">
                    {p}
                  </button>
                ))}
              </div>
            </div>}

            {/* Identity */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Email Address *</label>
                <input required value={form.email_address} onChange={e => setEmail(e.target.value)}
                  placeholder="you@domain.com" className="input-field" type="email" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Display Name</label>
                <input value={form.display_name} onChange={e => set('display_name', e.target.value)}
                  placeholder="John Smith" className="input-field" />
              </div>
            </div>

            {mode === 'microsoft_graph' && (
              <div className="p-4 rounded-xl bg-bg-elevated border border-border text-xs text-text-secondary space-y-1">
                <p>After you click <strong className="text-white">Add &amp; Connect</strong>, you'll be sent to Microsoft to sign in as this mailbox and approve access.</p>
                <p className="text-text-muted">Sending, reading and Junk-folder rescue all go through Microsoft Graph — no SMTP AUTH or IMAP needed.</p>
              </div>
            )}

            {mode === 'smtp' && <>
            {/* SMTP */}
            <div className="p-4 rounded-xl bg-bg-elevated border border-border space-y-3">
              <p className="text-xs font-bold text-orange uppercase tracking-wider">SMTP — Sending</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-text-secondary mb-1">Host *</label>
                  <input required value={form.smtp_host} onChange={e => set('smtp_host', e.target.value)}
                    placeholder="smtp.gmail.com" className="input-field" />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Port</label>
                  <input type="number" value={form.smtp_port} onChange={e => set('smtp_port', e.target.value)}
                    className="input-field" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Username *</label>
                  <input required value={form.smtp_user} onChange={e => set('smtp_user', e.target.value)}
                    placeholder="you@domain.com" className="input-field" />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Password *</label>
                  <div className="relative">
                    <input required type={showPass.smtp ? 'text' : 'password'}
                      value={form.smtp_password} onChange={e => set('smtp_password', e.target.value)}
                      placeholder="App password" className="input-field pr-8" />
                    <button type="button" onClick={() => setShowPass(s => ({...s, smtp: !s.smtp}))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white">
                      {showPass.smtp ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* IMAP */}
            <div className="p-4 rounded-xl bg-bg-elevated border border-border space-y-3">
              <p className="text-xs font-bold text-green uppercase tracking-wider">IMAP — Reading & Replying</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-text-secondary mb-1">Host *</label>
                  <input required value={form.imap_host} onChange={e => set('imap_host', e.target.value)}
                    placeholder="imap.gmail.com" className="input-field" />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Port</label>
                  <input type="number" value={form.imap_port} onChange={e => set('imap_port', e.target.value)}
                    className="input-field" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Username *</label>
                  <input required value={form.imap_user} onChange={e => set('imap_user', e.target.value)}
                    placeholder="you@domain.com" className="input-field" />
                </div>
                <div>
                  <label className="block text-xs text-text-secondary mb-1">Password *</label>
                  <div className="relative">
                    <input required type={showPass.imap ? 'text' : 'password'}
                      value={form.imap_password} onChange={e => set('imap_password', e.target.value)}
                      placeholder="App password" className="input-field pr-8" />
                    <button type="button" onClick={() => setShowPass(s => ({...s, imap: !s.imap}))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white">
                      {showPass.imap ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              </div>
            </div>
            </>}

            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
              <button id="add-mailbox-submit" type="submit" disabled={loading} className="btn-primary flex-1">
                {loading ? 'Adding...' : mode === 'microsoft_graph' ? 'Add & Connect' : 'Add Mailbox'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body
  )
}

// ── External Contacts Section ────────────────────────────────────────────────

const externalContactsApi = {
  list:   ()           => api.get('/external-contacts'),
  add:    (data)       => api.post('/external-contacts', data),
  remove: (id)         => api.delete(`/external-contacts/${id}`),
}

function AddManualContactModal({ onClose, onAdded }) {
  const [form, setForm]   = useState({ email_address: '', display_name: '', notes: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await externalContactsApi.add(form)
      onAdded()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add contact')
    } finally { setLoading(false) }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm">
      <div className="min-h-full flex items-start justify-center p-4 pt-24 pb-16">
        <div className="glass-card rounded-2xl w-full max-w-md animate-slide-up">
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div>
              <h2 className="text-lg font-bold text-white">Add Manual Contact</h2>
              <p className="text-xs text-text-secondary mt-0.5">No password needed — they reply manually</p>
            </div>
            <button onClick={onClose} className="text-text-muted hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={submit} className="p-6 space-y-4">
            {error && <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Email Address *</label>
              <input required type="email" value={form.email_address}
                onChange={e => setForm(f => ({...f, email_address: e.target.value}))}
                placeholder="colleague@strikin.com" className="input-field" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Display Name</label>
              <input value={form.display_name}
                onChange={e => setForm(f => ({...f, display_name: e.target.value}))}
                placeholder="John Smith" className="input-field" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Notes</label>
              <input value={form.notes}
                onChange={e => setForm(f => ({...f, notes: e.target.value}))}
                placeholder="e.g. Replies 9 PM – 7 AM (night shift)" className="input-field" />
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancel</button>
              <button type="submit" disabled={loading} className="btn-primary flex-1">
                {loading ? 'Adding...' : 'Add Contact'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body
  )
}

function ExternalContactsPanel() {
  const [contacts, setContacts]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [showModal, setShowModal] = useState(false)

  const load = async () => {
    try { const { data } = await externalContactsApi.list(); setContacts(data) }
    catch {} finally { setLoading(false) }
  }

  const remove = async (id) => {
    if (!confirm('Remove this contact from the manual pool?')) return
    await externalContactsApi.remove(id)
    load()
  }

  useEffect(() => { load() }, [])

  return (
    <div className="glass-card rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-accent animate-pulse-slow" />
            Manual Seed Pool
          </h2>
          <p className="text-xs text-text-secondary mt-0.5">
            Team members who receive warmup emails and reply manually — no SMTP needed
          </p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-secondary text-xs py-1.5 px-3">
          <Plus className="w-3.5 h-3.5" /> Add Contact
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">{[...Array(2)].map((_, i) => <div key={i} className="skeleton h-12 rounded-xl" />)}</div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-8 text-text-muted text-sm">
          <Mail className="w-8 h-8 mx-auto mb-2 opacity-30" />
          No manual contacts yet. Add team members from strikin.com or other orgs.
        </div>
      ) : (
        <div className="space-y-2">
          {contacts.map(c => (
            <div key={c.id} className="flex items-center justify-between p-3 rounded-xl bg-bg-elevated border border-border">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-accent/20 border border-blue-accent/30 flex items-center justify-center">
                  <span className="text-xs font-bold text-blue-400">
                    {(c.display_name || c.email_address)[0].toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{c.display_name || c.email_address}</p>
                  {c.display_name && <p className="text-xs text-text-muted">{c.email_address}</p>}
                  {c.notes && <p className="text-xs text-text-muted italic mt-0.5">{c.notes}</p>}
                </div>
              </div>
              <button onClick={() => remove(c.id)} className="text-text-muted hover:text-red-400 transition-colors p-1">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <AddManualContactModal
          onClose={() => setShowModal(false)}
          onAdded={() => { setShowModal(false); load() }}
        />
      )}
    </div>
  )
}

export default function Mailboxes() {
  const [mailboxes, setMailboxes] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [running, setRunning]     = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [oauthResult] = useState(() => {
    const ok = searchParams.get('oauth_success')
    const err = searchParams.get('oauth_error')
    if (ok) return { ok: true, text: `Connected ${ok}` }
    if (err) return { ok: false, text: `Connection failed: ${err}${searchParams.get('detail') ? ` — ${searchParams.get('detail')}` : ''}` }
    return null
  })

  // Clear the OAuth query params once read so a refresh doesn't show the banner again
  useEffect(() => { if (oauthResult) setSearchParams({}, { replace: true }) }, [])

  const load = async () => {
    setLoading(true)
    try { const { data } = await mailboxApi.list(); setMailboxes(data) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleRunWarmup = async () => {
    setRunning(true)
    try {
      await warmupApi.run()
      alert('Warmup cycle started in background! Check back in a few minutes.')
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to start warmup')
    } finally { setRunning(false) }
  }

  const active = mailboxes.filter(m => m.warmup_status === 'active').length

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Mailboxes</h1>
          <p className="text-text-secondary text-sm mt-0.5">{mailboxes.length} mailboxes · {active} active</p>
        </div>
        <div className="flex items-center gap-3">
          <button id="run-warmup-btn" onClick={handleRunWarmup} disabled={running || active < 2}
            className="btn-secondary text-sm"
            title={active < 2 ? 'Need at least 2 active mailboxes' : ''}>
            <Zap className="w-4 h-4 text-orange" />
            {running ? 'Running...' : 'Run Warmup Now'}
          </button>
          <button id="add-mailbox-btn" onClick={() => setShowModal(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> Add Mailbox
          </button>
        </div>
      </div>

      {oauthResult && (
        <div className={clsx('p-4 rounded-xl border flex items-start gap-3 text-sm',
          oauthResult.ok ? 'bg-green/10 border-green/20 text-green' : 'bg-red-500/10 border-red-500/20 text-red-400')}>
          {oauthResult.ok ? <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> : <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />}
          <p>{oauthResult.text}</p>
        </div>
      )}

      {/* Info banner */}
      {mailboxes.length > 0 && active < 2 && (
        <div className="p-4 rounded-xl bg-orange/10 border border-orange/20 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-orange flex-shrink-0 mt-0.5" />
          <p className="text-sm text-orange">
            You need at least <strong>2 active mailboxes</strong> to run warmup. Mailboxes warm each other up — more mailboxes = better scores.
          </p>
        </div>
      )}

      {/* Automated Mailboxes Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <div key={i} className="skeleton h-72 rounded-2xl" />)}
        </div>
      ) : mailboxes.length === 0 ? (
        <div className="glass-card rounded-2xl p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-orange/10 border border-orange/20 flex items-center justify-center mx-auto mb-4">
            <Mail className="w-8 h-8 text-orange" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">No Mailboxes Yet</h3>
          <p className="text-text-secondary text-sm mb-6 max-w-sm mx-auto">
            Add your first mailbox to start the warmup process. You need at least 2 mailboxes to begin.
          </p>
          <button onClick={() => setShowModal(true)} className="btn-primary mx-auto">
            <Plus className="w-4 h-4" /> Add First Mailbox
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {mailboxes.map(m => (
            <MailboxCard key={m.id} mailbox={m} onRefresh={load} />
          ))}
        </div>
      )}

      {/* Manual Seed Pool Panel */}
      <ExternalContactsPanel />

      {showModal && (
        <AddMailboxModal
          onClose={() => setShowModal(false)}
          onAdded={() => { setShowModal(false); load() }}
        />
      )}
    </div>
  )
}

