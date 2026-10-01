function csrfToken(): string {
  const cookie = document.cookie
    .split('; ')
    .find(part => part.startsWith('tei_csrf='))

  return decodeURIComponent(cookie?.split('=')[1] ?? '')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.method && options.method !== 'GET'
      ? { 'X-CSRF-Token': csrfToken() }
      : {}),
    ...options.headers,
  }

  const response = await fetch('/api/v1' + path, {
    ...options,
    credentials: 'same-origin',
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string'
      ? body.detail
      : Array.isArray(body?.detail)
        ? body.detail.map((issue: { msg: string }) => issue.msg.replace(/^Value error, /, '')).join('. ')
        : 'No se pudo completar la operación'
    throw new Error(detail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
