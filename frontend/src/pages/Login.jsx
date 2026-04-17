import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { GoogleLogin } from '@react-oauth/google'
import { Mail, Lock, Eye, EyeOff, Zap, Shield, TrendingUp, CheckCircle, User, Building, Phone, X, ArrowLeft } from 'lucide-react'
import api from '../api/client'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

export default function Login() {
  const navigate = useNavigate()
  const { login, googleLogin } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [mode, setMode]         = useState('login') // 'login' | 'request' | 'success'

  const [reqForm, setReqForm]       = useState({ full_name: '', email: '', company_name: '', phone: '', message: '' })
  const [reqLoading, setReqLoading] = useState(false)
  const [reqError, setReqError]     = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault(); setError(''); setLoading(true)
    const res = await login(form.email, form.password)
    setLoading(false)
    if (res.success) navigate('/dashboard')
    else setError(res.error)
  }

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('')
    const res = await googleLogin(credentialResponse.credential)
    if (res.success) navigate('/dashboard')
    else setError(res.error)
  }

  const handleRequest = async (e) => {
    e.preventDefault()
    setReqError(''); setReqLoading(true)
    try {
      await api.post('/access-requests/submit', reqForm)
      setMode('success')
    } catch (err) {
      setReqError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally { setReqLoading(false) }
  }

  const features = [
    { icon: TrendingUp, text: 'Gradual volume ramp — Week 1: 3/day → Week 8: 60/day' },
    { icon: Shield,     text: 'Auto open + reply via IMAP — signals domain trust' },
    { icon: Zap,        text: 'Real-time warmup score with inbox placement analytics' },
    { icon: CheckCircle,text: 'Multi-company isolation — each client sees only their data' },
  ]

  return (
    <div className="min-h-screen bg-bg-base flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-orange/5 via-transparent to-green/5" />
        <div className="absolute top-0 left-0 w-96 h-96 bg-orange/8 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-80 h-80 bg-green/8 rounded-full blur-3xl translate-x-1/4 translate-y-1/4" />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange to-orange-dark flex items-center justify-center shadow-orange-glow">
              <Zap className="w-5 h-5 text-white" fill="white" />
            </div>
            <div>
              <p className="text-xs text-text-secondary font-medium tracking-widest uppercase">Neurogenix</p>
              <h1 className="text-lg font-bold text-white leading-none">WarmUp</h1>
            </div>
          </div>
        </div>

        <div className="relative z-10">
          <h2 className="text-4xl font-black text-white leading-tight mb-4">
            Your emails deserve to<br />land in the{' '}
            <span className="text-gradient-orange">inbox.</span>
          </h2>
          <p className="text-text-secondary text-lg mb-10 leading-relaxed">
            Professional email warmup at scale. Build domain reputation,
            boost deliverability, and send with confidence.
          </p>
          <div className="space-y-4">
            {features.map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-orange/10 border border-orange/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-orange" />
                </div>
                <p className="text-text-secondary text-sm leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10">
          <p className="text-text-muted text-xs">
            Powered by <span className="text-orange font-semibold">Neurogenix</span> — AI-Powered Growth Infrastructure
          </p>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-md animate-fade-in">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange to-orange-dark flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" fill="white" />
            </div>
            <div>
              <p className="text-[10px] text-text-secondary font-medium tracking-widest uppercase">Neurogenix</p>
              <h1 className="text-base font-bold text-white leading-none">WarmUp</h1>
            </div>
          </div>

          {/* ── LOGIN MODE ── */}
          {mode === 'login' && (
            <div className="glass-card rounded-2xl p-8">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-white mb-1">Welcome back</h2>
                <p className="text-text-secondary text-sm">Sign in to your warmup dashboard</p>
              </div>

              {error && (
                <div className="mb-5 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full bg-red-500/20 flex items-center justify-center text-xs">!</span>
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input id="login-email" type="email" placeholder="you@company.com"
                      value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))}
                      className="input-field !pl-10" required autoComplete="email" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input id="login-password" type={showPass ? 'text' : 'password'} placeholder="Your password"
                      value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))}
                      className="input-field !pl-10 !pr-10" required autoComplete="current-password" />
                    <button type="button" onClick={() => setShowPass(s => !s)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button id="login-submit" type="submit" disabled={loading} className="btn-primary w-full mt-2 py-3">
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                      Signing in...
                    </span>
                  ) : 'Sign In'}
                </button>
              </form>

              {/* Google Sign-In — only shown when Client ID is configured */}
              {GOOGLE_CLIENT_ID && (
                <>
                  <div className="flex items-center gap-3 my-5">
                    <div className="flex-1 h-px bg-border" />
                    <span className="text-xs text-text-muted">or continue with</span>
                    <div className="flex-1 h-px bg-border" />
                  </div>
                  <div className="flex justify-center">
                    <GoogleLogin
                      onSuccess={handleGoogleSuccess}
                      onError={() => setError('Google sign-in failed. Try email/password instead.')}
                      theme="filled_black"
                      shape="pill"
                      text="signin_with"
                      size="large"
                    />
                  </div>
                </>
              )}

              <div className="mt-5 pt-5 border-t border-border">
                <p className="text-text-muted text-xs text-center">
                  Don't have an account?{' '}
                  <button onClick={() => setMode('request')} className="text-orange hover:underline font-medium">
                    Request Access
                  </button>
                </p>
              </div>
            </div>
          )}

          {/* ── REQUEST ACCESS MODE ── */}
          {mode === 'request' && (
            <div className="glass-card rounded-2xl p-8">
              <div className="flex items-center gap-3 mb-6">
                <button onClick={() => setMode('login')} className="text-text-muted hover:text-white transition-colors">
                  <ArrowLeft className="w-4 h-4" />
                </button>
                <div>
                  <h2 className="text-2xl font-bold text-white">Request Access</h2>
                  <p className="text-text-secondary text-sm">Our team will review and get back to you</p>
                </div>
              </div>

              {reqError && (
                <div className="mb-5 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{reqError}</div>
              )}

              <form onSubmit={handleRequest} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Full Name *</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input required type="text" placeholder="John Smith"
                      value={reqForm.full_name} onChange={e => setReqForm(f => ({...f, full_name: e.target.value}))}
                      className="input-field !pl-10" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Work Email *</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input required type="email" placeholder="you@company.com"
                      value={reqForm.email} onChange={e => setReqForm(f => ({...f, email: e.target.value}))}
                      className="input-field !pl-10" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Company Name *</label>
                  <div className="relative">
                    <Building className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input required type="text" placeholder="Acme Corp"
                      value={reqForm.company_name} onChange={e => setReqForm(f => ({...f, company_name: e.target.value}))}
                      className="input-field !pl-10" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Phone (optional)</label>
                  <div className="relative">
                    <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                    <input type="tel" placeholder="+91 98765 43210"
                      value={reqForm.phone} onChange={e => setReqForm(f => ({...f, phone: e.target.value}))}
                      className="input-field !pl-10" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1.5">Tell us about your use case</label>
                  <textarea rows={3} placeholder="e.g. We need to warm up 6 domains for a real estate outreach campaign..."
                    value={reqForm.message} onChange={e => setReqForm(f => ({...f, message: e.target.value}))}
                    className="input-field resize-none" />
                </div>
                <button type="submit" disabled={reqLoading} className="btn-primary w-full py-3 mt-1">
                  {reqLoading ? 'Submitting...' : 'Submit Request'}
                </button>
              </form>
            </div>
          )}

          {/* ── SUCCESS MODE ── */}
          {mode === 'success' && (
            <div className="glass-card rounded-2xl p-10 text-center">
              <div className="w-16 h-16 rounded-full bg-green/10 border border-green/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Request Submitted!</h2>
              <p className="text-text-secondary text-sm mb-6">
                We've received your request. The Neurogenix team will review it and reach out to you at <strong className="text-white">{reqForm.email}</strong> within 24 hours.
              </p>
              <button onClick={() => setMode('login')} className="btn-secondary mx-auto">
                <ArrowLeft className="w-4 h-4" /> Back to Sign In
              </button>
            </div>
          )}

          <p className="text-center text-text-muted text-xs mt-6">
            © {new Date().getFullYear()} Neurogenix. Enterprise Email Warmup Platform.
          </p>
        </div>
      </div>
    </div>
  )
}
