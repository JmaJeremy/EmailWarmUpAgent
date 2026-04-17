import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { mailboxApi, warmupApi } from '../api/client'
import { ArrowLeft, TrendingUp, Mail, MessageSquare, BarChart3, Calendar } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts'

const WEEK_LIMITS = { 1:3, 2:6, 3:12, 4:20, 5:30, 6:40, 7:50, 8:60 }

function ScoreRing({ score }) {
  const r = 52, c = 2 * Math.PI * r
  const offset = c - (score / 100) * c
  const color = score >= 80 ? '#00D68F' : score >= 50 ? '#FF6B35' : '#EF4444'
  return (
    <div className="flex flex-col items-center">
      <svg width={130} height={130} viewBox="0 0 130 130">
        <circle cx="65" cy="65" r={r} fill="none" stroke="#1E2436" strokeWidth="10" />
        <circle cx="65" cy="65" r={r} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 65 65)"
          style={{ transition: 'stroke-dashoffset 1.2s ease-out' }} />
        <text x="65" y="60" textAnchor="middle" fill="white" fontSize="26" fontWeight="800">{Math.round(score)}</text>
        <text x="65" y="78" textAnchor="middle" fill="#64748B" fontSize="11">/ 100</text>
      </svg>
      <p className="text-sm font-semibold text-white mt-1">Warmup Score</p>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-elevated border border-border rounded-xl px-4 py-3 shadow-lg">
      <p className="text-xs text-text-secondary mb-2">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-text-secondary">{p.name}:</span>
          <span className="text-white font-semibold">{typeof p.value === 'number' && p.value < 1 ? `${(p.value * 100).toFixed(0)}%` : p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function WarmupStats() {
  const { mailboxId } = useParams()
  const [mailbox, setMailbox] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [mbRes, logsRes] = await Promise.all([
          mailboxApi.get(mailboxId),
          warmupApi.logs(mailboxId, 30),
        ])
        setMailbox(mbRes.data)
        setLogs(logsRes.data)
      } finally { setLoading(false) }
    }
    load()
  }, [mailboxId])

  if (loading) return (
    <div className="space-y-5 animate-fade-in">
      <div className="skeleton h-8 w-48 rounded-xl" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-28 rounded-2xl" />)}
      </div>
    </div>
  )

  if (!mailbox) return (
    <div className="text-center py-20">
      <p className="text-text-secondary">Mailbox not found</p>
      <Link to="/mailboxes" className="btn-primary mt-4 mx-auto">Back to Mailboxes</Link>
    </div>
  )

  const weekLimit = WEEK_LIMITS[mailbox.current_week] || 60
  const lastLog = logs[logs.length - 1]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back */}
      <Link to="/mailboxes" className="inline-flex items-center gap-2 text-text-secondary hover:text-white text-sm transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Mailboxes
      </Link>

      {/* Header */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex flex-col lg:flex-row items-start lg:items-center gap-6">
          <ScoreRing score={mailbox.warmup_score || 0} />
          <div className="flex-1">
            <h1 className="text-2xl font-black text-white mb-1">{mailbox.email_address}</h1>
            <p className="text-text-secondary text-sm mb-4">{mailbox.display_name}</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Week', value: `${mailbox.current_week}/8`, color: 'text-orange' },
                { label: 'Daily Limit', value: `${weekLimit}`, color: 'text-blue-accent' },
                { label: 'Total Sent', value: mailbox.total_sent, color: 'text-white' },
                { label: 'Status', value: mailbox.warmup_status, color: mailbox.warmup_status === 'active' ? 'text-green' : 'text-text-secondary' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-bg-elevated rounded-xl p-3 border border-border">
                  <p className={`text-lg font-black capitalize ${color}`}>{value}</p>
                  <p className="text-xs text-text-muted">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Week progress visual */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-base font-bold text-white mb-4">8-Week Warmup Progress</h2>
        <div className="flex gap-2">
          {[...Array(8)].map((_, i) => {
            const w = i + 1
            const isDone = w < mailbox.current_week
            const isCurrent = w === mailbox.current_week
            return (
              <div key={w} className="flex-1 text-center">
                <div className={`h-8 rounded-lg mb-1.5 flex items-center justify-center text-xs font-bold transition-all ${
                  isDone ? 'bg-green text-bg-base' :
                  isCurrent ? 'bg-orange text-white shadow-orange-glow' :
                  'bg-bg-elevated border border-border text-text-muted'
                }`}>
                  {isDone ? '✓' : w}
                </div>
                <p className="text-[9px] text-text-muted">{WEEK_LIMITS[w]}/d</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Daily volume */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-base font-bold text-white mb-1">Daily Volume (30 days)</h2>
          <p className="text-xs text-text-secondary mb-4">Emails sent, opened & replied</p>
          {logs.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={logs} margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2436" />
                <XAxis dataKey="date" tick={{ fill: '#4A5568', fontSize: 9 }} tickFormatter={v => v.slice(5)} />
                <YAxis tick={{ fill: '#4A5568', fontSize: 9 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="sent" fill="#FF6B35" radius={[3,3,0,0]} name="Sent" />
                <Bar dataKey="opened" fill="#00D68F" radius={[3,3,0,0]} name="Opened" />
                <Bar dataKey="replied" fill="#4D9CFF" radius={[3,3,0,0]} name="Replied" />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyChart />}
        </div>

        {/* Score trend */}
        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-base font-bold text-white mb-1">Score Trend</h2>
          <p className="text-xs text-text-secondary mb-4">Daily warmup health score</p>
          {logs.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={logs} margin={{ left: -20 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00D68F" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00D68F" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2436" />
                <XAxis dataKey="date" tick={{ fill: '#4A5568', fontSize: 9 }} tickFormatter={v => v.slice(5)} />
                <YAxis domain={[0, 100]} tick={{ fill: '#4A5568', fontSize: 9 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="score" stroke="#00D68F" strokeWidth={2}
                  fill="url(#scoreGrad)" name="Score" />
              </AreaChart>
            </ResponsiveContainer>
          ) : <EmptyChart />}
        </div>
      </div>

      {/* Log table */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-base font-bold text-white mb-4">Activity Log</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                {['Date', 'Week', 'Sent', 'Opened', 'Replied', 'Open%', 'Reply%', 'Score'].map(h => (
                  <th key={h} className="text-left py-2.5 px-3 text-text-muted font-semibold uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...logs].reverse().slice(0, 15).map((log, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-bg-elevated transition-colors">
                  <td className="py-2.5 px-3 text-text-secondary">{log.date}</td>
                  <td className="py-2.5 px-3 text-orange font-semibold">{log.week}</td>
                  <td className="py-2.5 px-3 text-white">{log.sent}</td>
                  <td className="py-2.5 px-3 text-green">{log.opened}</td>
                  <td className="py-2.5 px-3 text-blue-accent">{log.replied}</td>
                  <td className="py-2.5 px-3 text-text-secondary">{(log.open_rate * 100).toFixed(0)}%</td>
                  <td className="py-2.5 px-3 text-text-secondary">{(log.reply_rate * 100).toFixed(0)}%</td>
                  <td className="py-2.5 px-3">
                    <span className="font-bold" style={{ color: log.score >= 80 ? '#00D68F' : log.score >= 50 ? '#FF6B35' : '#EF4444' }}>
                      {log.score.toFixed(1)}
                    </span>
                  </td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={8} className="text-center py-8 text-text-muted">No activity logs yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function EmptyChart() {
  return (
    <div className="h-48 flex flex-col items-center justify-center text-center">
      <BarChart3 className="w-8 h-8 text-text-muted mb-2" />
      <p className="text-text-muted text-xs">No data yet — start warmup to see charts</p>
    </div>
  )
}
