/**
 * Export report data to a downloadable CSV file for clinic accounting.
 */
export function exportReportToCSV(reportData) {
  if (!reportData || !reportData.reconciliation) return;

  const recon = reportData.reconciliation;
  const analytics = reportData.analytics || {};
  const date = recon.date;
  const clinicId = recon.clinic_id;

  const lines = [];

  // Title
  lines.push(`SWASTHIQ EOD FINANCIAL RECONCILIATION & ANALYTICS REPORT`);
  lines.push(`Clinic ID,${clinicId}`);
  lines.push(`Report Date,${date}`);
  lines.push(`Generated At,${new Date().toISOString()}`);
  lines.push(``);

  // Section 1: EOD Reconciliation Summary
  lines.push(`--- EOD FINANCIAL RECONCILIATION ---`);
  lines.push(`Metric,Amount (Rupees),Amount (Paise)`);
  lines.push(`Total Billed,${(recon.total_billed_paise / 100).toFixed(2)},${recon.total_billed_paise}`);
  lines.push(`Total Discounts,${(recon.total_discount_paise / 100).toFixed(2)},${recon.total_discount_paise}`);
  lines.push(`Total Net Collected,${(recon.total_collected_paise / 100).toFixed(2)},${recon.total_collected_paise}`);
  lines.push(`Outstanding Balance,${(recon.outstanding_paise / 100).toFixed(2)},${recon.outstanding_paise}`);
  lines.push(`Total Refunds,${(recon.total_refunds_paise / 100).toFixed(2)},${recon.total_refunds_paise}`);
  lines.push(`Total Sales Visits,${recon.total_visits},`);
  lines.push(`Total Refund Visits,${recon.total_refund_visits},`);
  lines.push(``);

  // Section 2: Payment Mode Breakdown
  lines.push(`--- PAYMENT CHANNEL BREAKDOWN ---`);
  lines.push(`Channel,Gross Billed (₹),Discount (₹),Net Collected (₹),Outstanding (₹),Refunds (₹)`);
  (recon.by_payment_mode || []).forEach((pm) => {
    lines.push(
      `${pm.payment_mode.toUpperCase()},` +
      `${(pm.total_billed_paise / 100).toFixed(2)},` +
      `${(pm.total_discount_paise / 100).toFixed(2)},` +
      `${(pm.total_collected_paise / 100).toFixed(2)},` +
      `${(pm.outstanding_paise / 100).toFixed(2)},` +
      `${(pm.total_refunds_paise / 100).toFixed(2)}`
    );
  });
  lines.push(``);

  // Section 3: Prescriber Performance
  if (analytics.doctor_performance && analytics.doctor_performance.length > 0) {
    lines.push(`--- PRESCRIBER PERFORMANCE ---`);
    lines.push(`Doctor ID,Consultations,Total Revenue (₹),Avg Revenue/Visit (₹)`);
    analytics.doctor_performance.forEach((doc) => {
      const avg = doc.visit_count > 0 ? (doc.total_revenue_paise / doc.visit_count / 100).toFixed(2) : '0.00';
      lines.push(`${doc.doctor_id},${doc.visit_count},${(doc.total_revenue_paise / 100).toFixed(2)},${avg}`);
    });
    lines.push(``);
  }

  // Section 4: Top Prescribed Medications
  if (analytics.top_drugs_by_quantity && analytics.top_drugs_by_quantity.length > 0) {
    lines.push(`--- TOP MEDICATIONS BY VOLUME ---`);
    lines.push(`Rank,Drug Name,Units Dispensed`);
    analytics.top_drugs_by_quantity.forEach((d) => {
      lines.push(`${d.rank},${d.drug_name},${d.value}`);
    });
    lines.push(``);
  }

  // Section 5: Top Revenue Generating Medications
  if (analytics.top_drugs_by_revenue && analytics.top_drugs_by_revenue.length > 0) {
    lines.push(`--- TOP MEDICATIONS BY REVENUE ---`);
    lines.push(`Rank,Drug Name,Gross Revenue (₹)`);
    analytics.top_drugs_by_revenue.forEach((d) => {
      lines.push(`${d.rank},${d.drug_name},${(d.value / 100).toFixed(2)}`);
    });
  }

  const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(lines.join("\n"));
  const link = document.createElement("a");
  link.setAttribute("href", csvContent);
  link.setAttribute("download", `SwasthiQ_EOD_Audit_${clinicId}_${date}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
