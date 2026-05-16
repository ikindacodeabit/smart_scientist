// Renders synthesis text, turning [PAPERID] tokens into hoverable citation chips.
// Also renders ## / # prefixed lines as section headings.
const SPLIT_RE    = /(\[[A-Za-z0-9]+\])/g
const IS_CITATION = /^\[[A-Za-z0-9]+\]$/

function renderInline(text, hoveredId, onEnter, onLeave) {
  return text.split(SPLIT_RE).map((part, i) => {
    if (IS_CITATION.test(part)) {
      const id = part.slice(1, -1)
      const isActive = hoveredId === id
      return (
        <span
          key={i}
          className={`citation-chip${isActive ? ' citation-chip--active' : ''}`}
          onMouseEnter={() => onEnter(id)}
          onMouseLeave={onLeave}
        >
          {part}
        </span>
      )
    }
    return <span key={i}>{part}</span>
  })
}

function parseSynthesis(text, hoveredId, onEnter, onLeave) {
  const paragraphs = text.split(/\n\n+/)

  return paragraphs.map((para, pIdx) => {
    if (para.startsWith('### ')) {
      return <h4 key={pIdx} className="synthesis-heading">{para.slice(4)}</h4>
    }
    if (para.startsWith('## ')) {
      return <h3 key={pIdx} className="synthesis-heading">{para.slice(3)}</h3>
    }
    if (para.startsWith('# ')) {
      return <h3 key={pIdx} className="synthesis-heading">{para.slice(2)}</h3>
    }
    return (
      <p key={pIdx} className="synthesis-paragraph">
        {renderInline(para, hoveredId, onEnter, onLeave)}
      </p>
    )
  })
}

export default function CitedAnswer({ synthesis, hoveredPaperId, onCitationHover }) {
  return (
    <div className="synthesis-text">
      {parseSynthesis(synthesis, hoveredPaperId, onCitationHover, () => onCitationHover(null))}
    </div>
  )
}
