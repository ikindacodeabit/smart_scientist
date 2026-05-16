export default function PaperCard({ paper, highlighted }) {
  const displayAuthors =
    paper.authors.length > 2
      ? paper.authors.slice(0, 2).join(', ') + ' et al.'
      : paper.authors.join(', ') || 'Unknown authors'

  const hasLinks = paper.doi || paper.open_access_url

  return (
    <div className={`paper-card${highlighted ? ' paper-card--highlighted' : ''}`}>
      <span className="paper-id-label">{paper.paper_id.slice(0, 8)}</span>

      <h3 className="paper-title">{paper.title}</h3>
      <p className="paper-authors">{displayAuthors}</p>

      <div className="paper-meta-row">
        <span>{paper.year || 'n.d.'}</span>
        <span className="paper-citations">{paper.citation_count} citations</span>
        <div className="relevance-dots">
          {[1, 2, 3].map((n) => (
            <span
              key={n}
              className={`relevance-dot ${n <= paper.relevance_score ? 'relevance-dot--filled' : 'relevance-dot--empty'}`}
            />
          ))}
        </div>
      </div>

      {hasLinks && (
        <div className="paper-links">
          {paper.doi && (
            <a
              className="paper-doi-link"
              href={`https://doi.org/${paper.doi}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              DOI ↗
            </a>
          )}
          {paper.open_access_url && (
            <a
              className="paper-oa-badge"
              href={paper.open_access_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open Access
            </a>
          )}
        </div>
      )}
    </div>
  )
}
