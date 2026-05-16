import { useRef, useEffect } from 'react'

const MAX_HEIGHT = 180

export default function QuestionInput({ value, onChange, onSubmit, disabled }) {
  const textareaRef = useRef(null)

  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, MAX_HEIGHT) + 'px'
  }, [value])

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      if (!disabled && value.trim()) onSubmit()
    }
  }

  return (
    <div className="question-input-wrapper">
      <textarea
        ref={textareaRef}
        className="question-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe a specific, technical research question..."
        disabled={disabled}
        rows={3}
      />
      <button
        className="question-submit-btn"
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
      >
        Investigate <span className="submit-arrow">→</span>
      </button>
    </div>
  )
}
