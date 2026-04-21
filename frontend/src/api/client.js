const BASE_URL = '/api'

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Dashboard
  getDashboardStats: () => request('/metrics/dashboard'),
  getRollingAverages: (days = 30) => request(`/metrics/rolling-averages?days=${days}`),
  getByPlatform: (days = 7) => request(`/metrics/by-platform?days=${days}`),
  getTopPosts: (days = 30, limit = 10) => request(`/metrics/top-posts?days=${days}&limit=${limit}`),

  // Posts
  listPosts: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/posts${q ? '?' + q : ''}`)
  },
  getPost: (id) => request(`/posts/${id}`),
  getPendingApproval: () => request('/posts/pending-approval'),
  getNeedsReview: () => request('/posts/needs-review'),
  generatePost: (data) => request('/posts/generate', { method: 'POST', body: JSON.stringify(data) }),
  createPost: (data) => request('/posts/', { method: 'POST', body: JSON.stringify(data) }),
  updatePost: (id, data) => request(`/posts/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  approvePost: (id, data) => request(`/posts/${id}/approve`, { method: 'POST', body: JSON.stringify(data) }),
  deletePost: (id) => request(`/posts/${id}`, { method: 'DELETE' }),
  getPostMetricsHistory: (id) => request(`/metrics/post/${id}/history`),
  getPostVsAverage: (id) => request(`/metrics/post/${id}/vs-average`),

  // Assets
  listAssets: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/assets${q ? '?' + q : ''}`)
  },
  getAsset: (id) => request(`/assets/${id}`),
  deleteAsset: (id) => request(`/assets/${id}`, { method: 'DELETE' }),
  uploadAsset: (formData) => fetch(`${BASE_URL}/assets/upload`, { method: 'POST', body: formData }).then(r => r.json()),

  // Trends
  listTrends: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return request(`/trends${q ? '?' + q : ''}`)
  },
  getTrendingSounds: (platform) => request(`/trends/sounds${platform ? '?platform=' + platform : ''}`),
  getTrendingHashtags: (platform) => request(`/trends/hashtags${platform ? '?platform=' + platform : ''}`),
  getViralBenchmarks: (platform) => request(`/trends/viral-benchmarks${platform ? '?platform=' + platform : ''}`),
  addViralBenchmark: (data) => request('/trends/viral-benchmarks', { method: 'POST', body: JSON.stringify(data) }),
  refreshTrends: () => request('/trends/refresh', { method: 'POST' }),

  // Suggestions
  getSuggestions: () => request('/suggestions/next-posts'),

  // Reports
  listReports: () => request('/reports/'),
  getLatestReport: () => request('/reports/latest'),
  generateReport: () => request('/reports/generate', { method: 'POST' }),

  // Settings
  getSettings: () => request('/settings/'),
  updateSettings: (data) => request('/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  getBrandBible: () => request('/settings/brand-bible'),
}
