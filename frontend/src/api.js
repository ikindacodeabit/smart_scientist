const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export async function startRun(question) {
  const res = await fetch(`${BASE_URL}/api/question`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Server error ${res.status}: ${text}`)
  }
  return res.json()
}

export function createEventSource(runId, { onProgress, onComplete, onError }) {
  const es = new EventSource(`${BASE_URL}/api/stream/${runId}`)

  es.onmessage = (e) => {
    let data
    try {
      data = JSON.parse(e.data)
    } catch {
      return
    }

    if (data.type === 'progress') {
      onProgress(data)
    } else if (data.type === 'complete') {
      onComplete(data)
    } else if (data.type === 'error') {
      onError(data.message)
    }
    // 'ping' events are ignored
  }

  es.onerror = () => {
    onError('Connection lost. Please try again.')
    es.close()
  }

  return es
}
