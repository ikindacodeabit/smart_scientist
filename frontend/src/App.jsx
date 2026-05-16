import { useState, useRef, useEffect } from 'react'
import { startRun, createEventSource } from './api.js'
import QuestionInput from './components/QuestionInput.jsx'
import ProgressTracker from './components/ProgressTracker.jsx'
import ResultView from './components/ResultView.jsx'

const STATES = { IDLE: 'idle', RUNNING: 'running', COMPLETE: 'complete', ERROR: 'error' }

const EXAMPLES = [
  "What are the failure mechanisms of ALD Al₂O₃ in high-aspect-ratio trenches?",
  "How does grain boundary segregation affect fracture in nanocrystalline tungsten?",
  "What limits thermal conductivity in amorphous silicon at cryogenic temperatures?",
]

export default function App() {
  const [appState, setAppState]           = useState(STATES.IDLE)
  const [question, setQuestion]           = useState('')
  const [progressEvents, setProgressEvents] = useState([])
  const [result, setResult]               = useState(null)
  const [error, setError]                 = useState(null)
  const eventSourceRef                    = useRef(null)

  const handleSubmit = async () => {
    const q = question.trim()
    if (!q) return

    setAppState(STATES.RUNNING)
    setProgressEvents([])
    setResult(null)
    setError(null)

    try {
      const { run_id } = await startRun(q)
      const es = createEventSource(run_id, {
        onProgress: (evt) => setProgressEvents((prev) => [...prev, evt]),
        onComplete: (data) => {
          setResult(data.result)
          setAppState(STATES.COMPLETE)
          es.close()
        },
        onError: (msg) => {
          setError(msg)
          setAppState(STATES.ERROR)
          es.close()
        },
      })
      eventSourceRef.current = es
    } catch (e) {
      setError(e.message)
      setAppState(STATES.ERROR)
    }
  }

  const handleReset = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setAppState(STATES.IDLE)
    setQuestion('')
    setProgressEvents([])
    setResult(null)
    setError(null)
  }

  // Clean up SSE on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  if (appState === STATES.IDLE) {
    return (
      <div className="idle-view">
        <div className="idle-content">
          <h1 className="idle-heading">Ask the Scientist</h1>
          <p className="idle-subheading">
            Evidence-backed answers to technical research questions.
          </p>
          <QuestionInput
            value={question}
            onChange={setQuestion}
            onSubmit={handleSubmit}
            disabled={false}
          />
          <div className="example-chips">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="example-chip"
                onClick={() => setQuestion(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (appState === STATES.RUNNING) {
    return (
      <div className="running-view">
        <p className="running-question">{question}</p>
        <ProgressTracker events={progressEvents} />
      </div>
    )
  }

  if (appState === STATES.COMPLETE) {
    return (
      <div className="complete-view">
        <p className="result-question-label">{result.question}</p>
        <ResultView result={result} />
        <button className="reset-button" onClick={handleReset}>
          Ask another question
        </button>
      </div>
    )
  }

  // ERROR state
  return (
    <div className="error-view">
      <h2 className="error-heading">Something went wrong</h2>
      <pre className="error-message">{error}</pre>
      <button className="reset-button" onClick={handleReset}>
        Try again
      </button>
    </div>
  )
}
