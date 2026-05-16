import { useState } from 'react'
import UncertaintyBadge from './UncertaintyBadge.jsx'
import CitedAnswer from './CitedAnswer.jsx'
import PaperCard from './PaperCard.jsx'

export default function ResultView({ result }) {
  const [hoveredPaperId, setHoveredPaperId] = useState(null)

  const { synthesis, uncertainty, papers_filtered } = result

  return (
    <div>
      <UncertaintyBadge uncertainty={uncertainty} />

      <div className="result-section">
        <CitedAnswer
          synthesis={synthesis}
          hoveredPaperId={hoveredPaperId}
          onCitationHover={setHoveredPaperId}
        />
      </div>

      {papers_filtered.length > 0 && (
        <div className="result-section">
          <h2 className="result-section-heading">Evidence</h2>
          <div className="papers-grid">
            {papers_filtered.map((paper) => (
              <PaperCard
                key={paper.paper_id}
                paper={paper}
                highlighted={hoveredPaperId === paper.paper_id}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
