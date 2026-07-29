import { formatPaise } from '../api/client';

export default function ReconciliationDashboard({ data }) {
  if (!data) {
    return (
      <div className="empty-state-card">
        <div className="empty-state-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="40" height="40">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
          </svg>
        </div>
        <h3>No Ingestion File Loaded</h3>
        <p>Select a date from the header menu or click "Upload Log" to ingest a daily billing file.</p>
      </div>
    );
  }

  const {
    total_billed_paise,
    total_collected_paise,
    outstanding_paise,
    total_refunds_paise,
    total_discount_paise,
    total_visits,
    total_refund_visits,
    by_payment_mode,
    validation_errors,
    date,
  } = data;

  const collectionRate = total_billed_paise > 0 
    ? Math.round((total_collected_paise / (total_billed_paise - total_discount_paise)) * 100) 
    : 100;

  return (
    <div className="dashboard-content">
      {/* Overview Banner */}
      <div className="overview-banner">
        <div>
          <span className="banner-tag">Daily Ledger</span>
          <h1 className="banner-title">EOD Reconciliation Audit ({date})</h1>
          <p className="banner-desc">
            Audited financial settlement across {total_visits} sale transaction(s) and {total_refund_visits} refund adjustment(s).
          </p>
        </div>
        <div className="banner-stat">
          <div className="rate-circle">{collectionRate}%</div>
          <div className="rate-label">Collection Efficiency</div>
        </div>
      </div>

      {/* KPI Ribbon Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Gross Invoiced</span>
            <span className="kpi-badge indigo">Billed</span>
          </div>
          <div className="kpi-value">{formatPaise(total_billed_paise)}</div>
          <div className="kpi-subtext">Sum of all prescribed line items</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Actual Collections</span>
            <span className="kpi-badge emerald">Settled</span>
          </div>
          <div className="kpi-value emerald-text">{formatPaise(total_collected_paise)}</div>
          <div className="kpi-subtext">Verified received funds</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Outstanding Balance</span>
            <span className={`kpi-badge ${outstanding_paise > 0 ? 'amber' : 'neutral'}`}>
              {outstanding_paise > 0 ? 'Pending' : 'Cleared'}
            </span>
          </div>
          <div className={`kpi-value ${outstanding_paise > 0 ? 'amber-text' : ''}`}>
            {formatPaise(outstanding_paise)}
          </div>
          <div className="kpi-subtext">Net billed minus collections</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Refund Adjustments</span>
            <span className={`kpi-badge ${total_refunds_paise > 0 ? 'rose' : 'neutral'}`}>
              {total_refunds_paise > 0 ? 'Active' : 'None'}
            </span>
          </div>
          <div className={`kpi-value ${total_refunds_paise > 0 ? 'rose-text' : ''}`}>
            {formatPaise(total_refunds_paise)}
          </div>
          <div className="kpi-subtext">{total_refund_visits} refund record(s)</div>
        </div>
      </div>

      {total_discount_paise > 0 && (
        <div className="discount-strip">
          <span>Total Promotional Discounts Applied</span>
          <strong>{formatPaise(total_discount_paise)}</strong>
        </div>
      )}

      {/* Settlement Breakdown Table */}
      <div className="section-card">
        <div className="section-header">
          <div>
            <h2 className="section-title">Payment Channel Breakdown</h2>
            <p className="section-subtitle">Financial distribution split by payment mechanism</p>
          </div>
        </div>

        <table className="ledger-table">
          <thead>
            <tr>
              <th>Channel</th>
              <th className="num-col">Gross Billed</th>
              <th className="num-col">Discount</th>
              <th className="num-col">Net Collected</th>
              <th className="num-col">Outstanding</th>
              <th className="num-col">Refunds</th>
              <th className="num-col">Channel Share</th>
            </tr>
          </thead>
          <tbody>
            {by_payment_mode?.map((pm) => {
              const sharePct = total_collected_paise > 0
                ? Math.round((pm.total_collected_paise / total_collected_paise) * 100)
                : 0;

              return (
                <tr key={pm.payment_mode}>
                  <td>
                    <span className={`channel-tag ${pm.payment_mode}`}>
                      <span className="channel-dot" />
                      {pm.payment_mode.toUpperCase()}
                    </span>
                  </td>
                  <td className="num-col">{formatPaise(pm.total_billed_paise)}</td>
                  <td className="num-col muted-text">{formatPaise(pm.total_discount_paise)}</td>
                  <td className="num-col bold-text">{formatPaise(pm.total_collected_paise)}</td>
                  <td className={`num-col ${pm.outstanding_paise > 0 ? 'amber-text' : 'muted-text'}`}>
                    {formatPaise(pm.outstanding_paise)}
                  </td>
                  <td className={`num-col ${pm.total_refunds_paise > 0 ? 'rose-text' : 'muted-text'}`}>
                    {formatPaise(pm.total_refunds_paise)}
                  </td>
                  <td className="num-col">
                    <div className="share-bar-cell">
                      <span>{sharePct}%</span>
                      <div className="share-track">
                        <div className={`share-fill ${pm.payment_mode}`} style={{ width: `${sharePct}%` }} />
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Validation Errors Notice */}
      {validation_errors?.length > 0 && (
        <div className="error-log-card">
          <div className="error-log-header">
            <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
            </svg>
            <span>{validation_errors.length} Record(s) Flagged & Skipped During Ingestion</span>
          </div>
          <div className="error-log-list">
            {validation_errors.map((err, i) => (
              <div key={i} className="error-log-row">{err}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
