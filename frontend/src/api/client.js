import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ng_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('ng_token')
      localStorage.removeItem('ng_user')
      localStorage.removeItem('ng_company')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login:       (email, password) => api.post('/auth/login', { email, password }),
  googleLogin: (credential)      => api.post('/auth/google', { credential }),
  register:    (data)            => api.post('/auth/register', data),
  me:          ()                => api.get('/auth/me'),
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardApi = {
  overview: () => api.get('/dashboard/overview'),
  superAdminOverview: () => api.get('/dashboard/super-admin'),
}

// ── Mailboxes ─────────────────────────────────────────────────────────────────
export const mailboxApi = {
  list: (companyId) => api.get('/mailboxes/', { params: companyId ? { company_id: companyId } : {} }),
  add: (data) => api.post('/mailboxes/', data),
  get: (id) => api.get(`/mailboxes/${id}`),
  update: (id, data) => api.patch(`/mailboxes/${id}`, data),
  delete: (id) => api.delete(`/mailboxes/${id}`),
  startWarmup: (id) => api.post(`/mailboxes/${id}/start-warmup`),
  pauseWarmup: (id) => api.post(`/mailboxes/${id}/pause-warmup`),
  testConnection: (id) => api.post(`/mailboxes/${id}/test`),
  uploadLogo: (companyId, formData) =>
    api.post(`/companies/${companyId}/logo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// ── Companies ─────────────────────────────────────────────────────────────────
export const companyApi = {
  list:           ()             => api.get('/companies/'),
  approve:        (id)           => api.post(`/companies/${id}/approve`),
  suspend:        (id)           => api.post(`/companies/${id}/suspend`),
  create:         (data)         => api.post('/companies/create', data),
  update:         (id, data)     => api.patch(`/companies/${id}`, data),
  getDetail:      (id)           => api.get(`/companies/${id}/detail`),
  changePassword: (id, password) => api.post(`/companies/${id}/change-password`, { new_password: password }),
  uploadLogo: (id, formData) =>
    api.post(`/companies/${id}/logo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}

// ── Warmup ────────────────────────────────────────────────────────────────────
export const warmupApi = {
  run: () => api.post('/warmup/run'),
  runAll: () => api.post('/warmup/run-all'),
  runMailbox: (id) => api.post(`/warmup/run-mailbox/${id}`),
  logs: (mailboxId, days = 30) => api.get(`/warmup/logs/${mailboxId}`, { params: { days } }),
  status: () => api.get('/warmup/status'),
}
