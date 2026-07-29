export default function NarrativePage({ data }) {
  if (!data) {
    return (
      <div className="empty-state-card">
        <h3>No Executive Brief Generated</h3>
        <p>Upload a billing log or select a date to view the AI executive summary.</p>
      </div>
    );
  }

  const { narrative, traced_figures, llm_model, error, date } = data;

  return (
    <div className="dashboard-content">
      <div className="page-header">
        <h1 className="page-title">Executive Briefing Memo</h1>
        <p className="page-subtitle">
          AI-synthesized operational overview for {date} · Model: {llm_model || 'Grounded Pipeline'}
        </p>
      </div>

      {error && (
        <div className="notice-card">
          <strong>Pipeline Note:</strong> {error.replace(/[\u2014\u2013—–]/g, ':')}
        </div>
      )}

      <div className="brief-layout">
        {/* Memo Card */}
        <div className="section-card memo-card">
          <div className="memo-meta-header">
            <div>
              <div className="memo-company">MEHTA MULTI-SPECIALTY CLINIC</div>
              <div className="memo-title-sub">END OF DAY OPERATIONAL BRIEFING</div>
            </div>
            <div className="memo-date-badge">{date}</div>
          </div>

          <div className="memo-divider" />

          <div className="memo-body-text">
            {formatBrief(narrative)}
          </div>

          <div className="memo-footer">
            <span>Verified Grounded Synthesis</span>
            <span>Zero Hallucinated Figures Guarantee</span>
          </div>
        </div>

        {/* Lineage Ledger */}
        <div className="section-card">
          <div className="section-header">
            <h2 className="section-title">Data Lineage & Traced Figures</h2>
            <p className="section-subtitle">Deterministic verification mapping every figure to source database fields</p>
          </div>

          <div className="lineage-list">
            {traced_figures?.length > 0 ? (
              traced_figures.map((tf, i) => (
                <div key={i} className="lineage-row">
                  <div className="lineage-val">{tf.figure}</div>
                  <div className="lineage-arrow">→</div>
                  <div className="lineage-field">{tf.source_field}</div>
                  {tf.source_value && (
                    <div className="lineage-raw">= {tf.source_value}</div>
                  )}
                </div>
              ))
            ) : (
              <div className="lineage-empty">No traced figures generated for this brief</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatBrief(text) {
  if (!text) return null;
  const cleanText = text.replace(/[\u2014\u2013—–]/g, ':');
  const parts = cleanText.split(/(\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('*') && part.endsWith('*')) {
      return <strong key={i}>{part.slice(1, -1)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}
