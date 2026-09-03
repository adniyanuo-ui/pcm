import type {
  FormulaCandidate,
  RagApiCandidate,
  RagSearchPayload,
  RagSearchResult,
} from '../types/consultation'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class AuthenticationRequiredError extends Error {}

export function isRagApiConfigured(): boolean {
  return Boolean(apiBaseUrl)
}

export function hasCmsToken(): boolean {
  return Boolean(localStorage.getItem('token'))
}

export async function loginCms(username: string, password: string): Promise<void> {
  if (!apiBaseUrl) throw new Error('尚未配置后端 API 地址')
  const response = await fetch(apiBaseUrl + '/api/cms/user/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const body = await response.json()
  if (!response.ok || body.code !== 200 || !body.data?.token) {
    throw new Error(body.detail || body.msg || '登录失败，请检查账号和密码')
  }
  localStorage.setItem('token', body.data.token)
  localStorage.setItem('account', body.data.account || username)
}

export async function searchFormulas(payload: RagSearchPayload): Promise<RagSearchResult> {
  if (!apiBaseUrl) {
    throw new Error('尚未配置 VITE_API_BASE_URL')
  }
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 15_000)
  const token = localStorage.getItem('token') || ''
  try {
    const response = await fetch(apiBaseUrl + '/api/cms/llm/rag/search/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: 'Token ' + token } : {}),
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    const body = await response.json()
    if (response.status === 401 || body.code === 401) {
      localStorage.removeItem('token')
      throw new AuthenticationRequiredError('登录状态已失效，请重新登录')
    }
    if (!response.ok || body.code !== 200) {
      throw new Error(body.detail || body.msg || '检索失败（HTTP ' + response.status + '）')
    }
    return body.data as RagSearchResult
  } finally {
    window.clearTimeout(timeout)
  }
}

function firstPage(pages: number[]): number {
  return pages.length ? pages[0] : 0
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))]
}

export function toFormulaCandidate(candidate: RagApiCandidate): FormulaCandidate {
  const supports = unique(Object.values(candidate.matched_terms).flat()).slice(0, 7)
  const source = candidate.fields['方源'] || candidate.source.citation
  const action = candidate.fields['功用'] || ''
  const indication = candidate.fields['主治'] || candidate.fields['正文及其他'] || ''
  const summary = action || (indication.length > 90 ? indication.slice(0, 90) + '…' : indication)
  const cautions = candidate.quality_flags.length
    ? ['该条目带质量标记：' + candidate.quality_flags.join('、')]
    : ['召回阶段尚未生成不匹配点，需结合完整四诊复核']

  return {
    id: candidate.id,
    name: candidate.name,
    source,
    match: candidate.evidence_coverage,
    summary,
    supports: supports.length ? supports : candidate.match_reasons.slice(0, 4),
    cautions,
    composition: candidate.fields['组成'] || '辞典本条未提供组成字段',
    original: indication || '辞典本条未提供主治字段',
    citation: {
      volume: candidate.source.volume,
      pdfPage: firstPage(candidate.source.pdf_pages),
      bookPage: firstPage(candidate.source.book_pages),
    },
  }
}
