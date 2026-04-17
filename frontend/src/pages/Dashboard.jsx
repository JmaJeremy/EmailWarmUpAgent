import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { dashboardApi } from '../api/client'
import {
  TrendingUp, Mail, CheckCircle, Zap,
  BarChart3, ArrowUpRight, Clock, RefreshCw
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar
} from 'recharts'

function StatCard({ label, value, sub, icon: Icon, color = 'orange', trend }) {
  const colors = {
    orange: { bg: 'bg-orange/10', border: 'border-orange/20', text: 'text-orange', icon: 'text-orange' },
    green:  { bg: 'bg-green/10',  border: 'border-green/20',  text: 'text-green',  icon: 'text-green'  },
    blue:   { bg: 'bg-blue-accent/10', border: 'border-blue-accent/20', text: 'text-blue-accent', icon: 'text-blue-accent' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', icon: 'text-purple-400' },
  }
  const c = colors[color]
  return (
    <div className="glass-card rounded-2xl p-5 border hover:border-white/10 transition-all duration-300 hover:shadow-card-hover animate-fade-in">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl ${c.bg} border ${c.border} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${c.icon}`} />
        </div>
        {trend !== undefined && (
          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${trend >= 0 ? 'bg-green/10 text-green' : 'bg-red-500/10 text-red-400'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-3xl font-black text-white mb-1">{value}</p>
      <p className="text-sm font-semibold text-white">{label}</p>
      {sub && <p className="text-xs text-text-secondary mt-0.5">{sub}</p>}
    </div>
  )
}

function WarmupScoreBadge({ score }) {
  const size = 80
  const radius = 34
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 80 ? '#00D68F' : score >= 50 ? '#FF6B35' : '#EF4444'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx="40" cy="40" r={radius} fill="none" stroke="#1E2436" strokeWidth="8" />
        <circle
          cx="40" cy="40" r={radius} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
        <text x="40" y="44" textAnchor="middle" fill="white" fontSize="14" fontWeight="700">{score}</text>
      </svg>
      <p className="text-xs text-text-secondary mt-1">Avg Score</p>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-elevated border border-border rounded-xl px-4 py-3 shadow-card">
      <p className="text-xs text-text-secondary mb-2">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-text-secondary capitalize">{p.name}:</span>
          <span className="text-white font-semibold">{p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { company } = useAuth()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data: d } = await dashboardApi.overview()
      setData(d)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="animate-fade-in space-y-5">
      <div className="skeleton h-8 w-64 rounded-xl" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-36 rounded-2xl" />)}
      </div>
      <div className="skeleton h-64 rounded-2xl" />
    </div>
  )

  const d = data || {}
  const today = d.today || {}
  const week = d.this_week || {}
  const mailboxes = d.mailboxes || {}
  const trend = d.trend || []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Dashboard</h1>
          <p className="text-text-secondary text-sm mt-0.5">
            {company?.name} — Warmup overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="dashboard-refresh"
            onClick={load}
            className="btn-ghost"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <Link to="/mailboxes" className="btn-primary">
            <Mail className="w-4 h-4" />
            Manage Mailboxes
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active Mailboxes" value={mailboxes.active || 0}
          sub={`${mailboxes.total || 0} total`} icon={Mail} color="orange" />
        <StatCard label="Sent Today" value={today.sent || 0}
          sub={`${week.sent || 0} this week`} icon={Zap} color="blue" />
        <StatCard label="Open Rate" value={`${today.open_rate || 0}%`}
          sub="Emails opened today" icon={TrendingUp} color="green" />
        <StatCard label="Reply Rate" value={`${today.reply_rate || 0}%`}
          sub="Emails replied today" icon={CheckCircle} color="purple" />
      </div>

      {/* Chart + Score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 30-day chart */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-white">30-Day Activity</h2>
              <p className="text-xs text-text-secondary">Emails sent, opened & replied</p>
            </div>
            <BarChart3 className="w-5 h-5 text-text-muted" />
          </div>
          {trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trend} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradSent" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#FF6B35" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#FF6B35" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradOpened" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00D68F" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00D68F" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2436" />
                <XAxis dataKey="date" tick={{ fill: '#4A5568', fontSize: 10 }} tickLine={false}
                  tickFormatter={v => v.slice(5)} />
                <YAxis tick={{ fill: '#4A5568', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="sent" stroke="#FF6B35" strokeWidth={2}
                  fill="url(#gradSent)" name="Sent" />
                <Area type="monotone" dataKey="opened" stroke="#00D68F" strokeWidth={2}
                  fill="url(#gradOpened)" name="Opened" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-center">
              <BarChart3 className="w-10 h-10 text-text-muted mb-3" />
              <p className="text-text-secondary text-sm">No warmup data yet</p>
              <p className="text-text-muted text-xs mt-1">Add mailboxes and start warmup to see trends</p>
            </div>
          )}
        </div>

        {/* Score + Top mailboxes */}
        <div className="glass-card rounded-2xl p-6 flex flex-col">
          <h2 className="text-base font-bold text-white mb-4">Warmup Health</h2>
          <div className="flex items-center justify-center mb-5">
            <WarmupScoreBadge score={Math.round(d.avg_warmup_score || 0)} />
          </div>
          <div className="space-y-2 flex-1">
            <p className="text-xs text-text-secondary font-semibold uppercase tracking-wider mb-3">Top Mailboxes</p>
            {(d.top_mailboxes || []).slice(0, 4).map((m, i) => (
              <div key={i} className="flex items-center gap-2.5 p-2.5 rounded-xl bg-bg-elevated border border-border hover:border-white/10 transition-colors">
                <div className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: m.score >= 80 ? '#00D68F' : m.score >= 50 ? '#FF6B35' : '#EF4444' }} />
                <p className="text-xs text-white truncate flex-1">{m.email}</p>
                <span className="text-xs font-bold text-white flex-shrink-0">{Math.round(m.score)}</span>
              </div>
            ))}
            {!d.top_mailboxes?.length && (
              <p className="text-text-muted text-xs text-center py-4">No mailboxes yet</p>
            )}
          </div>
          <Link to="/mailboxes" className="btn-secondary mt-4 text-xs">
            <ArrowUpRight className="w-3.5 h-3.5" />
            View All Mailboxes
          </Link>
        </div>
      </div>

      {/* Week summary */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-text-muted" />
          <h2 className="text-base font-bold text-white">This Week</h2>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Emails Sent', value: week.sent || 0, color: 'text-orange' },
            { label: 'Emails Opened', value: week.opened || 0, color: 'text-green' },
            { label: 'Emails Replied', value: week.replied || 0, color: 'text-blue-accent' },
          ].map(({ label, value, color }) => (
            <div key={label} className="text-center p-4 rounded-xl bg-bg-elevated border border-border">
              <p className={`text-2xl font-black ${color}`}>{value.toLocaleString()}</p>
              <p className="text-xs text-text-secondary mt-1">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Warmup Pool Visualizer */}
      <WarmupPoolVisualizer poolData={d.pool_data} />

      {/* 3-Week Schedule Table */}
      <WarmupScheduleTable poolData={d.pool_data} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// WARMUP POOL VISUALIZER — VIP left | Helpers+Manual right
// ─────────────────────────────────────────────────────────────────────────────
function WarmupPoolVisualizer({ poolData }) {
  if (!poolData) return null

  // Process dynamic pools
  const vipPool = (poolData.vips || []).map(m => ({ email: m.email, label: 'VIP' }))
  const helperPool = (poolData.helpers || []).map(m => ({ email: m.email, label: 'Helper' }))
  const manualPool = (poolData.manuals || []).map(m => ({ email: m.email, label: 'Manual' }))

  const [pulse, setPulse] = React.useState(0)
  React.useEffect(() => {
    const maxLen = Math.max(vipPool.length, helperPool.length + manualPool.length, 1)
    const t = setInterval(() => setPulse(p => (p + 1) % maxLen), 800)
    return () => clearInterval(t)
  }, [vipPool.length, helperPool.length, manualPool.length])

  const roleColor = (label) => ({
    VIP:    { bg: 'bg-orange/10', border: 'border-orange/30', dot: 'bg-orange',     text: 'text-orange' },
    Helper: { bg: 'bg-green/10',  border: 'border-green/30',  dot: 'bg-green',      text: 'text-green'  },
    Manual: { bg: 'bg-blue-accent/10', border: 'border-blue-accent/30', dot: 'bg-blue-accent', text: 'text-blue-accent' },
  }[label])

  const rightSide = [...helperPool, ...manualPool]

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-bold text-white">Live Warmup Pool</h2>
          <p className="text-xs text-text-secondary mt-0.5">Who talks to whom: VIPs (company domains) ↔ Helpers & Manual Contacts</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange" /> VIP</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green" /> Helper</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-accent" /> Manual</span>
        </div>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-start">
        {/* LEFT — VIP Mailboxes */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-orange uppercase tracking-wider mb-3">VIP Domains ({vipPool.length})</p>
          {vipPool.map((m, i) => {
            const c = roleColor(m.label)
            const isActive = pulse === i
            return (
              <div key={m.email}
                className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all duration-300 ${
                  isActive ? `${c.bg} ${c.border} shadow-sm` : 'bg-bg-elevated border-border'
                }`}>
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${isActive ? c.dot + ' animate-pulse' : 'bg-text-muted'}`} />
                <p className="text-xs text-white truncate font-mono">{m.email}</p>
              </div>
            )
          })}
          {vipPool.length === 0 && <p className="text-xs text-text-muted italic">No VIPs found.</p>}
        </div>

        {/* CENTER — Flow arrows */}
        <div className="flex flex-col items-center justify-center pt-8 gap-1">
          <div className="flex flex-col items-center gap-1">
            {['→', '→', '→'].map((a, i) => (
              <span key={i} className="text-orange text-sm opacity-60 animate-pulse-slow">{a}</span>
            ))}
          </div>
          <div className="w-px h-8 bg-gradient-to-b from-orange/50 to-green/50" />
          <div className="flex flex-col items-center gap-1">
            {['←', '←', '←'].map((a, i) => (
              <span key={i} className="text-green text-sm opacity-60 animate-pulse-slow">{a}</span>
            ))}
          </div>
          <p className="text-[9px] text-text-muted text-center mt-1 max-w-[50px]">send &amp; reply</p>
        </div>

        {/* RIGHT — Helpers + Manual */}
        <div className="space-y-2">
          <p className="text-xs font-bold text-green uppercase tracking-wider mb-3">Helpers + Manual ({rightSide.length})</p>
          {rightSide.map((m, i) => {
            const c = roleColor(m.label)
            const isActive = i < vipPool.length ? pulse === (vipPool.length - 1 - i) : false
            return (
              <div key={m.email}
                className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all duration-300 ${
                  isActive ? `${c.bg} ${c.border}` : 'bg-bg-elevated border-border'
                }`}>
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.dot} ${isActive ? 'animate-pulse' : 'opacity-40'}`} />
                <p className="text-xs text-white truncate font-mono flex-1">{m.email}</p>
                <span className={`text-[9px] px-1.5 py-0.5 rounded ${c.bg} ${c.text} font-bold flex-shrink-0`}>
                  {m.label}
                </span>
              </div>
            )
          })}
          {rightSide.length === 0 && <p className="text-xs text-text-muted italic">No helpers or manual contacts found.</p>}
        </div>
      </div>

      <div className="mt-4 p-3 rounded-xl bg-bg-elevated border border-border text-xs text-text-secondary">
        💡 <strong className="text-white">How it works:</strong> Each VIP mailbox picks random targets daily from this active pool.
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SCHEDULE TABLE — dynamic per-day email counts per VIP mailbox based on its daily_limit
// ─────────────────────────────────────────────────────────────────────────────
function WarmupScheduleTable({ poolData }) {
  if (!poolData || !poolData.vips || poolData.vips.length === 0) return null

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const vips = poolData.vips
  
  // Calculate total weekly sent dynamically
  const dailyTotal = vips.reduce((sum, v) => sum + (v.daily_limit || 0), 0)
  const weeklyTotal = dailyTotal * 7
  const poolSize = vips.length + (poolData.helpers || []).length + (poolData.manuals || []).length

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-bold text-white">Daily Warmup Configurations</h2>
          <p className="text-xs text-text-secondary mt-0.5">Based on individual mailbox limits</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        {[
          { label: 'Avg Emails/day per VIP', value: Math.round(dailyTotal/vips.length), color: 'text-orange' },
          { label: 'Total emails/day', value: `${dailyTotal}/day`, color: 'text-white' },
          { label: 'Total emails/week', value: `${weeklyTotal}/week`, color: 'text-green' },
        ].map(s => (
          <div key={s.label} className="p-3 rounded-xl bg-bg-elevated border border-border text-center">
            <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-[10px] text-text-muted mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-text-secondary mb-4 italic">Each mailbox dynamically targets {Math.round(dailyTotal/vips.length)} random contacts from the {poolSize}-person pool daily.</p>

      {/* Per-mailbox per-day table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-3 text-text-muted font-semibold w-64">VIP Mailbox</th>
              <th className="text-center py-2 px-2 text-text-muted font-semibold">Limit/Day</th>
              {days.map(d => (
                <th key={d} className="text-center py-2 px-2 text-text-muted font-semibold">{d}</th>
              ))}
              <th className="text-center py-2 px-2 text-text-muted font-semibold">Week Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {vips.map((mail, ri) => (
              <tr key={mail.email} className="hover:bg-bg-elevated/50 transition-colors">
                <td className="py-2.5 pr-3">
                  <span className="font-mono text-orange text-xs">{mail.email}</span>
                </td>
                <td className="text-center py-2.5 px-2">
                  <span className="font-bold text-text-secondary bg-bg-elevated px-2 py-1 rounded">{mail.daily_limit}</span>
                </td>
                {days.map((d, di) => {
                  // Slight daily variation mapped to UI
                  const variation = (ri + di) % 3 === 0 ? -1 : (ri + di) % 3 === 1 ? 0 : 1
                  const count = Math.max(1, mail.daily_limit + variation)
                  return (
                    <td key={d} className="text-center py-2.5 px-2">
                      <span className="font-bold text-white">{count}</span>
                    </td>
                  )
                })}
                <td className="text-center py-2.5 px-2">
                  <span className="font-black text-orange">{mail.daily_limit * 7}</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-border bg-bg-elevated/30">
              <td colSpan={2} className="py-2.5 pr-3 text-right text-xs font-bold text-white">All VIP Total</td>
              {days.map(d => (
                <td key={d} className="text-center py-2.5 px-2 font-black text-green text-xs">{dailyTotal}</td>
              ))}
              <td className="text-center py-2.5 px-2 font-black text-green text-xs">{weeklyTotal}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Hourly breakdown */}
      <div className="mt-5 p-4 rounded-xl bg-orange/5 border border-orange/20">
        <p className="text-xs font-bold text-orange mb-2">📅 How emails are spread hourly (9 AM → 9 PM IST)</p>
        <div className="flex gap-1 flex-wrap">
          {Array.from({ length: 12 }, (_, i) => {
            const hour = 9 + i
            const perHourTotal = Math.ceil(dailyTotal / 12)
            return (
              <div key={hour} className="flex flex-col items-center p-1.5 rounded-lg bg-bg-base border border-border/50">
                <span className="text-[9px] text-text-muted">{hour}:00</span>
                <span className="text-xs font-bold text-white mt-0.5">{perHourTotal}</span>
                <span className="text-[8px] text-text-muted">total</span>
              </div>
            )
          })}
        </div>
        <p className="text-[10px] text-text-muted mt-2">
          ≈ {Math.ceil(dailyTotal / 12)} emails/hour across all VIPs · Random targets picked fresh each hour
        </p>
      </div>
    </div>
  )
}
