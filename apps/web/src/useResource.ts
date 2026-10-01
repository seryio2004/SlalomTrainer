import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'

/** Shared loading and mutation state for pages backed by a single API resource. */
export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const requestId = useRef(0)

  const reload = useCallback(async () => {
    const id = ++requestId.current
    setLoading(true)
    try {
      const result = await api<T>(path)
      if (id === requestId.current) {
        setData(result)
        setError('')
      }
    } catch (reason) {
      if (id === requestId.current) {
        setError(reason instanceof Error ? reason.message : 'No se pudo cargar la página')
      }
      throw reason
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [path])

  useEffect(() => {
    setData(null)
    void reload().catch(() => {})
    return () => { requestId.current += 1 }
  }, [reload])

  async function mutate(target: string, body?: object, method = 'POST') {
    setSaving(true)
    setError('')
    try {
      await api(target, {
        method,
        ...(body ? { body: JSON.stringify(body) } : {}),
      })
      await reload()
      return true
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo guardar')
      return false
    } finally {
      setSaving(false)
    }
  }

  return { data, error, loading, saving, reload, mutate }
}
