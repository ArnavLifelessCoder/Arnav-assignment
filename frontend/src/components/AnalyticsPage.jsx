import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts';
import { formatPaise, formatHour } from '../api/client';

const PAYMENT_COLORS = {
  cash: '#10b981',
  card: '#2563eb',
  upi: '#7c3aed',
};

export default function AnalyticsPage({ data, reconData }) {
  const [chartMetric, setChartMetric] = useState('revenue');

  if (!data) {
    return (
      <div className="empty-state-card">
        <h3>No Analytics Available</h3>
        <p>Upload a billing log or select a report date to view operational velocity and performance analytics.</p>
      </div>
    );
  }

  const {
    revenue_by_hour,
    peak_hour,
    peak_hour_revenue_paise,
    top_drugs_by_quantity,
    top_drugs_by_revenue,
    doctor_performance = [],
    avg_visit_value_paise = 0,
    avg_items_per_visit = 0.0,
    shifts = [],
    price_tiers = [],
    polypharmacy,
    effective_discount_rate_pct = 0.0,
    date,
  } = data;

  const chartData = revenue_by_hour.map((h) => ({
    name: formatHour(h.hour),
    hour: h.hour,
    revenue: h.revenue_paise / 100,
    revenuePaise: h.revenue_paise,
    visits: h.visit_count,
    isPeak: h.hour === peak_hour,
  }));

  // Payment mode chart data from reconData
  const paymentChartData = (reconData?.by_payment_mode || []).map((pm) => ({
    name: pm.payment_mode.toUpperCase(),
    value: pm.total_collected_paise / 100,
    paise: pm.total_collected_paise,
    mode: pm.payment_mode,
  }));

  const maxQty = top_drugs_by_quantity.length > 0 ? top_drugs_by_quantity[0].value : 1;
  const maxRev = top_drugs_by_revenue.length > 0 ? top_drugs_by_revenue[0].value : 1;

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
      <div className="light-tooltip">
        <div className="tooltip-title">{d.name}</div>
        <div className="tooltip-row">
          <span>Revenue</span>
          <strong>{formatPaise(d.revenuePaise)}</strong>
        </div>
        <div className="tooltip-row">
          <span>Consultations</span>
          <span>{d.visits} visit(s)</span>
        </div>
        {d.isPeak && <div className="tooltip-peak-tag">Peak Traffic Hour</div>}
      </div>
    );
  };

  const isEmpty = revenue_by_hour.length === 0 &&
    top_drugs_by_quantity.length === 0 &&
    top_drugs_by_revenue.length === 0;

  if (isEmpty) {
    return (
      <div className="dashboard-content">
        <div className="page-header">
          <h1 className="page-title">Operational Analytics</h1>
          <p className="page-subtitle">Report for {date}</p>
        </div>
        <div className="empty-state-card">
          <h3>No Transaction Velocity Data</h3>
          <p>This day contains zero sale transactions (empty log or refund-only record).</p>
        </div>
      </div>
    );
  }

  const multiPct = polypharmacy && (polypharmacy.single_item_visits + polypharmacy.multi_item_visits) > 0
    ? Math.round((polypharmacy.multi_item_visits / (polypharmacy.single_item_visits + polypharmacy.multi_item_visits)) * 100)
    : 0;

  return (
    <div className="dashboard-content">
      {/* Header */}
      <div className="page-header-flex">
        <div>
          <h1 className="page-title">Operational Analytics</h1>
          <p className="page-subtitle">Hourly revenue velocity, prescriber contributions, price tiers, and shift performance for {date}</p>
        </div>
        {peak_hour !== null && (
          <div className="peak-callout">
            <span className="callout-label">Peak Activity Hour</span>
            <strong className="callout-val">{formatHour(peak_hour)}</strong>
            <span className="callout-sub">{formatPaise(peak_hour_revenue_paise)} generated</span>
          </div>
        )}
      </div>

      {/* Primary Executive KPI Ribbon */}
      <div className="kpi-grid" style={{ marginBottom: '24px' }}>
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Average Consultation Value</span>
            <span className="kpi-badge indigo">AOV</span>
          </div>
          <div className="kpi-value">{formatPaise(avg_visit_value_paise)}</div>
          <div className="kpi-subtext">Average collected per invoice</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Items / Prescription</span>
            <span className="kpi-badge emerald">Basket</span>
          </div>
          <div className="kpi-value emerald-text">{avg_items_per_visit} items</div>
          <div className="kpi-subtext">Average unit count per patient</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Polypharmacy Rate</span>
            <span className="kpi-badge amber">Multi-Item</span>
          </div>
          <div className="kpi-value amber-text">{multiPct}%</div>
          <div className="kpi-subtext">{polypharmacy?.multi_item_visits || 0} multi-item prescriptions</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-title">Discount Leakage Rate</span>
            <span className="kpi-badge rose">Margin</span>
          </div>
          <div className="kpi-value rose-text">{effective_discount_rate_pct}%</div>
          <div className="kpi-subtext">Discounts relative to gross billed</div>
        </div>
      </div>

      {/* Operating Shift Breakdown */}
      {shifts.length > 0 && (
        <div className="section-card" style={{ marginBottom: '24px' }}>
          <div className="section-header">
            <h2 className="section-title">Operating Shift Distribution</h2>
            <p className="section-subtitle">Revenue and consultation activity split by time window</p>
          </div>
          <div className="kpi-grid">
            {shifts.map((s) => (
              <div key={s.shift_name} className="kpi-card" style={{ background: 'var(--bg-subtle)' }}>
                <div className="kpi-header">
                  <span className="kpi-title">{s.shift_name}</span>
                  <span className="kpi-badge indigo">{s.visit_count} visit(s)</span>
                </div>
                <div className="kpi-value">{formatPaise(s.revenue_paise)}</div>
                <div className="kpi-subtext">
                  Avg {formatPaise(s.visit_count > 0 ? Math.round(s.revenue_paise / s.visit_count) : 0)} / visit
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hourly Velocity Chart with Metric Switcher */}
      <div className="section-card">
        <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="section-title">Hourly Activity Velocity</h2>
            <p className="section-subtitle">Distribution of collections and traffic bucketed by UTC hour slot</p>
          </div>
          <div className="top-nav-tabs">
            <button
              className={`tab-link ${chartMetric === 'revenue' ? 'active' : ''}`}
              onClick={() => setChartMetric('revenue')}
            >
              Revenue (₹)
            </button>
            <button
              className={`tab-link ${chartMetric === 'visits' ? 'active' : ''}`}
              onClick={() => setChartMetric('visits')}
            >
              Patient Traffic
            </button>
          </div>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 12, right: 12, bottom: 8, left: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={{ stroke: '#cbd5e1' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => chartMetric === 'revenue' ? `₹${v}` : v}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f1f5f9' }} />
              <Bar dataKey={chartMetric} radius={[6, 6, 0, 0]} maxBarSize={44}>
                {chartData.map((entry, idx) => (
                  <Cell
                    key={idx}
                    fill={entry.isPeak ? '#2563eb' : '#93c5fd'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Price Tiers & Payment Share Row */}
      <div className="analytics-grid" style={{ marginBottom: '24px' }}>
        {/* Price Tier Distribution */}
        {price_tiers.length > 0 && (
          <div className="section-card">
            <div className="section-header">
              <h2 className="section-title">Medication Price-Tier Distribution</h2>
              <p className="section-subtitle">Revenue share by unit cost category</p>
            </div>
            <ul className="rank-list">
              {price_tiers.map((pt) => (
                <li key={pt.tier_name} className="rank-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <strong style={{ fontSize: '13px', color: 'var(--text-dark)' }}>{pt.tier_name}</strong>
                    <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--cobalt-primary)' }}>
                      {formatPaise(pt.revenue_paise)} ({pt.total_qty} units)
                    </span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill indigo"
                      style={{
                        width: `${Math.min(100, (pt.revenue_paise / (top_drugs_by_revenue.reduce((a, b) => a + b.value, 1))) * 100)}%`
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Payment Channel Donut Chart */}
        {paymentChartData.length > 0 && (
          <div className="section-card">
            <div className="section-header">
              <h2 className="section-title">Payment Channel Revenue Share</h2>
              <p className="section-subtitle">Settled collections by payment channel</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px' }}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={paymentChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {paymentChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PAYMENT_COLORS[entry.mode] || '#2563eb'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`₹${value.toLocaleString()}`, 'Collected']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Prescriber / Doctor Performance Table */}
      {doctor_performance.length > 0 && (
        <div className="section-card" style={{ marginBottom: '28px' }}>
          <div className="section-header">
            <h2 className="section-title">Prescriber Activity & Revenue Distribution</h2>
            <p className="section-subtitle">Consultation volume and revenue generated per doctor</p>
          </div>
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Doctor ID</th>
                <th className="num-col">Consultations</th>
                <th className="num-col">Total Revenue</th>
                <th className="num-col">Avg Revenue / Visit</th>
              </tr>
            </thead>
            <tbody>
              {doctor_performance.map((doc) => {
                const avgDoc = doc.visit_count > 0 ? Math.round(doc.total_revenue_paise / doc.visit_count) : 0;
                return (
                  <tr key={doc.doctor_id}>
                    <td>
                      <span className="channel-tag card">
                        <span className="channel-dot" />
                        {doc.doctor_id}
                      </span>
                    </td>
                    <td className="num-col bold-text">{doc.visit_count} visit(s)</td>
                    <td className="num-col bold-text">{formatPaise(doc.total_revenue_paise)}</td>
                    <td className="num-col muted-text">{formatPaise(avgDoc)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Leaderboard Rankings */}
      <div className="analytics-grid">
        <div className="section-card">
          <div className="section-header">
            <h2 className="section-title">Top Prescribed Medications (by Volume)</h2>
            <p className="section-subtitle">Ranked by aggregate unit quantity dispensed</p>
          </div>
          <ul className="rank-list">
            {top_drugs_by_quantity.map((drug) => (
              <li key={drug.drug_name} className="rank-item">
                <span className={`rank-badge rank-${drug.rank}`}>{drug.rank}</span>
                <span className="drug-name">{drug.drug_name}</span>
                <div className="progress-cell">
                  <div className="progress-track">
                    <div
                      className="progress-fill indigo"
                      style={{ width: `${(drug.value / maxQty) * 100}%` }}
                    />
                  </div>
                </div>
                <span className="rank-val">{drug.value} units</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="section-card">
          <div className="section-header">
            <h2 className="section-title">Top Revenue Generating Medications</h2>
            <p className="section-subtitle">Ranked by gross revenue contributions</p>
          </div>
          <ul className="rank-list">
            {top_drugs_by_revenue.map((drug) => (
              <li key={drug.drug_name} className="rank-item">
                <span className={`rank-badge rank-${drug.rank}`}>{drug.rank}</span>
                <span className="drug-name">{drug.drug_name}</span>
                <div className="progress-cell">
                  <div className="progress-track">
                    <div
                      className="progress-fill emerald"
                      style={{ width: `${(drug.value / maxRev) * 100}%` }}
                    />
                  </div>
                </div>
                <span className="rank-val">{formatPaise(drug.value)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
