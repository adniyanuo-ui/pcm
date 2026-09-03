const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

interface ApiEnvelope<T> {
  code: number
  msg: string
  data: T
  detail?: string
}

export class AuthenticationRequiredError extends Error {}

export function isApiConfigured(): boolean {
  return Boolean(apiBaseUrl)
}

export function hasCmsToken(): boolean {
  return Boolean(localStorage.getItem('token'))
}

export function clearCmsToken(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('account')
}

export async function loginCms(username: string, password: string): Promise<void> {
  if (!apiBaseUrl) throw new Error('尚未配置后端 API 地址')
  const response = await fetch(apiBaseUrl + '/api/cms/user/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const body = await response.json() as ApiEnvelope<{ token: string; account: string }>
  if (!response.ok || body.code !== 200 || !body.data?.token) {
    throw new Error(body.detail || body.msg || '登录失败，请检查账号和密码')
  }
  localStorage.setItem('token', body.data.token)
  localStorage.setItem('account', body.data.account || username)
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 15_000,
): Promise<T> {
  if (!apiBaseUrl) throw new Error('尚未配置 VITE_API_BASE_URL')
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  const token = localStorage.getItem('token') || ''
  try {
    const response = await fetch(apiBaseUrl + path, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: 'Token ' + token } : {}),
        ...(init.headers || {}),
      },
      signal: controller.signal,
    })
    const body = await response.json() as ApiEnvelope<T>
    if (response.status === 401 || body.code === 401) {
      clearCmsToken()
      throw new AuthenticationRequiredError('登录状态已失效，请重新登录')
    }
    if (!response.ok || body.code !== 200) {
      throw new Error(body.detail || body.msg || '请求失败（HTTP ' + response.status + '）')
    }
    return body.data
  } finally {
    window.clearTimeout(timeout)
  }
}
