import { api } from './client'

export const auth = {
  login: (username, password, otpToken) =>
    api.post('/api/auth/login/', {
      username,
      password,
      ...(otpToken ? { otp_token: otpToken } : {}),
    }),
  twoFactorStatus: () => api.get('/api/auth/two-factor/'),
  twoFactorBegin: () => api.post('/api/auth/two-factor/', {}),
  twoFactorConfirm: (token) => api.put('/api/auth/two-factor/', { token }),
  twoFactorDisable: (password) => api.delete('/api/auth/two-factor/', { password }),
  me: () => api.get('/api/auth/me/'),
  updateMe: (payload) => api.patch('/api/auth/me/', payload),
  changePassword: (payload) => api.post('/api/auth/change-password/', payload),
  users: (params) => api.get('/api/auth/users/', params),
  createUser: (payload) => api.post('/api/auth/users/', payload),
  updateUser: (id, payload) => api.patch(`/api/auth/users/${id}/`, payload),
  resetPassword: (id, newPassword) =>
    api.post(`/api/auth/users/${id}/reset_password/`, { new_password: newPassword }),
  accessLog: (params) => api.get('/api/auth/access-log/', params),
  accessLogSummary: () => api.get('/api/auth/access-log/summary/'),
}

export const campus = {
  gates: () => api.get('/api/campus/gates/'),
  createGate: (payload) => api.post('/api/campus/gates/', payload),
  updateGate: (id, payload) => api.patch(`/api/campus/gates/${id}/`, payload),
  departments: () => api.get('/api/campus/departments/'),
  createDepartment: (payload) => api.post('/api/campus/departments/', payload),
}

export const students = {
  list: (params) => api.get('/api/students/', params),
  get: (id) => api.get(`/api/students/${id}/`),
  create: (payload) => api.post('/api/students/', payload),
  update: (id, payload) => api.patch(`/api/students/${id}/`, payload),
  remove: (id) => api.delete(`/api/students/${id}/`),
  summary: () => api.get('/api/students/summary/'),
  importPreview: (file) => api.post('/api/students/import-preview/', toFormData({ file })),
  importCommit: (file, updateExisting) =>
    api.post(
      '/api/students/import-commit/',
      toFormData({ file, update_existing: updateExisting ? 'true' : 'false' }),
    ),
}

export const devices = {
  list: (params) => api.get('/api/devices/', params),
  get: (id) => api.get(`/api/devices/${id}/`),
  create: (payload) =>
    api.post('/api/devices/', payload.photo ? toFormData(payload) : payload),
  update: (id, payload) =>
    api.patch(`/api/devices/${id}/`, payload.photo ? toFormData(payload) : payload),
  remove: (id) => api.delete(`/api/devices/${id}/`),
  history: (id) => api.get(`/api/devices/${id}/history/`),
  transfer: (id, payload) => api.post(`/api/devices/${id}/transfer/`, payload),
  reportStolen: (id, details) => api.post(`/api/devices/${id}/report_stolen/`, { details }),
  pending: (params) => api.get('/api/devices/pending/', params),
  approve: (id, assetTag) => api.post(`/api/devices/${id}/approve/`, { asset_tag: assetTag }),
  reject: (id, reason) => api.post(`/api/devices/${id}/reject/`, { reason }),
  qrBlob: (id) => api.blob(`/api/devices/${id}/qr/`),
  summary: () => api.get('/api/devices/summary/'),

  flags: (params) => api.get('/api/devices/flags/', params),
  createFlag: (payload) => api.post('/api/devices/flags/', payload),
  resolveFlag: (id, note) =>
    api.post(`/api/devices/flags/${id}/resolve/`, { resolution_note: note }),

  permits: (params) => api.get('/api/devices/permits/', params),
  createPermit: (payload) => api.post('/api/devices/permits/', payload),
  revokePermit: (id) => api.post(`/api/devices/permits/${id}/revoke/`, {}),
}

/** Build multipart only when there is actually a file to send. */
export function toFormData(payload) {
  const form = new FormData()
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') return
    form.append(key, value)
  })
  return form
}

/** The signed-out student form. No token is ever attached to these. */
export const publicApi = {
  choices: () => api.publicGet('/api/public/choices/'),
  registerComputer: (payload) =>
    api.publicPost(
      '/api/public/register-computer/',
      payload.photo ? toFormData(payload) : payload,
    ),
  myComputers: (payload) => api.publicPost('/api/public/my-computers/', payload),
}

export const search = {
  /** Live typeahead. `signal` lets a superseded keystroke cancel its request. */
  suggest: (q, kinds, signal) =>
    api.get('/api/search/suggest/', { q, kinds }, { signal }),
}

export const checkpoint = {
  lookup: (q) => api.get('/api/checkpoint/lookup/', { q }),
  recordScan: (payload) => api.post('/api/checkpoint/scans/', payload),
  bulkScans: (scans) => api.post('/api/checkpoint/scans/bulk/', { scans }),
  scans: (params) => api.get('/api/checkpoint/scans/', params),
  dashboard: () => api.get('/api/checkpoint/dashboard/'),
  exportCsv: (params) => api.blob('/api/checkpoint/scans/export/', params),
}
