import React, { useState, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { companyApi } from '../api/client'
import { Upload, User, Palette, Building, CheckCircle } from 'lucide-react'

export default function Settings() {
  const { user, company } = useAuth()
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoSuccess, setLogoSuccess] = useState(false)
  const [colorSaved, setColorSaved] = useState(false)
  const [accent, setAccent] = useState(company?.accent_color || '#FF6B35')
  const fileRef = useRef()

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setLogoUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      await companyApi.uploadLogo(company.id, fd)
      setLogoSuccess(true)
      setTimeout(() => setLogoSuccess(false), 3000)
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed')
    } finally { setLogoUploading(false) }
  }

  const handleSaveColor = async () => {
    try {
      await companyApi.update(company.id, { accent_color: accent })
      setColorSaved(true)
      setTimeout(() => setColorSaved(false), 3000)
    } catch {}
  }

  const presetColors = ['#FF6B35','#00D68F','#4D9CFF','#A855F7','#F59E0B','#EC4899','#06B6D4','#84CC16']

  return (
    <div className="space-y-6 animate-fade-in max-w-2xl">
      <div>
        <h1 className="text-2xl font-black text-white">Settings</h1>
        <p className="text-text-secondary text-sm mt-0.5">Manage your company profile &amp; branding</p>
      </div>

      {/* Profile */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <User className="w-4 h-4 text-orange" />
          <h2 className="text-base font-bold text-white">Your Profile</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Full Name', value: user?.full_name || '' },
            { label: 'Email', value: user?.email || '' },
            { label: 'Role', value: user?.role?.replace('_',' ') || '' },
            { label: 'Company', value: company?.name || '' },
          ].map(({ label, value }) => (
            <div key={label}>
              <label className="block text-xs text-text-secondary mb-1.5">{label}</label>
              <input className="input-field capitalize" value={value} readOnly />
            </div>
          ))}
        </div>
      </div>

      {/* Logo */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Building className="w-4 h-4 text-orange" />
          <h2 className="text-base font-bold text-white">Company Logo</h2>
        </div>
        <p className="text-xs text-text-secondary">Upload your logo (PNG, JPG, WebP, SVG). Shows in sidebar &amp; admin panel.</p>
        <div
          className="border-2 border-dashed border-border rounded-2xl p-8 text-center hover:border-orange/40 transition-colors cursor-pointer"
          onClick={() => fileRef.current?.click()}
        >
          {company?.logo_url ? (
            <div className="flex flex-col items-center gap-3">
              <img src={`/api${company.logo_url}`} alt="Logo" className="h-16 object-contain" />
              <p className="text-xs text-text-secondary">Click to change logo</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-xl bg-bg-elevated border border-border flex items-center justify-center">
                <Upload className="w-6 h-6 text-text-muted" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Click to upload logo</p>
                <p className="text-xs text-text-muted mt-0.5">Recommended: 200×200px</p>
              </div>
            </div>
          )}
          <input ref={fileRef} type="file" className="hidden" accept="image/*" onChange={handleLogoUpload} />
        </div>
        {logoUploading && <p className="text-xs text-orange">Uploading...</p>}
        {logoSuccess && (
          <div className="flex items-center gap-2 text-green text-xs">
            <CheckCircle className="w-4 h-4" /> Logo uploaded successfully
          </div>
        )}
      </div>

      {/* Brand Color */}
      <div className="glass-card rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <Palette className="w-4 h-4 text-orange" />
          <h2 className="text-base font-bold text-white">Brand Color</h2>
        </div>
        <p className="text-xs text-text-secondary">Your accent color appears throughout the dashboard.</p>
        <div className="flex gap-2 flex-wrap">
          {presetColors.map(c => (
            <button key={c} onClick={() => setAccent(c)}
              className="w-9 h-9 rounded-xl border-2 transition-all hover:scale-110"
              style={{ backgroundColor: c, borderColor: accent === c ? '#fff' : 'transparent' }} />
          ))}
          <input type="color" value={accent} onChange={e => setAccent(e.target.value)}
            className="w-9 h-9 rounded-xl cursor-pointer border border-border bg-bg-elevated" />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-10 rounded-xl flex items-center px-3"
            style={{ backgroundColor: `${accent}22`, border: `1px solid ${accent}44` }}>
            <span className="text-xs font-bold" style={{ color: accent }}>Preview — {accent}</span>
          </div>
          <button onClick={handleSaveColor} className="btn-primary">
            {colorSaved ? <><CheckCircle className="w-4 h-4" /> Saved!</> : 'Save Color'}
          </button>
        </div>
      </div>
    </div>
  )
}
