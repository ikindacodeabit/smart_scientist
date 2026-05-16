const STEP_ORDER = ['decomposing', 'retrieving', 'filtering', 'extracting', 'synthesizing']

const STEP_LABELS = {
  decomposing:  'Decomposing',
  retrieving:   'Retrieving',
  filtering:    'Filtering',
  extracting:   'Extracting',
  synthesizing: 'Synthesizing',
}

export default function ProgressTracker({ events }) {
  const latestEvent  = events[events.length - 1]
  const activeStep   = latestEvent?.step
  const activeIndex  = STEP_ORDER.indexOf(activeStep)

  // Build a map of step → message for completed steps too
  const messageMap = {}
  for (const evt of events) {
    messageMap[evt.step] = evt.message
  }

  return (
    <div className="progress-tracker">
      {STEP_ORDER.map((step, i) => {
        const isComplete = activeIndex >= 0 && i < activeIndex
        const isActive   = step === activeStep
        const isPending  = !isComplete && !isActive

        let stateClass = 'step--pending'
        if (isComplete) stateClass = 'step--complete'
        if (isActive)   stateClass = 'step--active'

        return (
          <div key={step} className={`step ${stateClass}`}>
            <div className="step-indicator">
              {isComplete && <span className="step-check">✓</span>}
              {isActive   && <span className="step-pulse" />}
              {isPending  && <span className="step-dot" />}
            </div>
            <div className="step-content">
              <span className="step-label">{STEP_LABELS[step]}</span>
              {isActive && latestEvent?.message && (
                <span className="step-message">{latestEvent.message}</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
