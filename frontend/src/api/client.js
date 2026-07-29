/**
 * API client for the SwasthiQ backend.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '');

export async function uploadBillingLog(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
  }

  return response.json();
}

export async function listReports() {
  const response = await fetch(`${API_BASE}/reports`);
  if (!response.ok) throw new Error('Failed to fetch reports');
  return response.json();
}

export async function getFullReport(clinicId, date) {
  const response = await fetch(`${API_BASE}/reports/${clinicId}/${date}`);
  if (!response.ok) throw new Error('Report not found');
  return response.json();
}

export async function getReconciliation(clinicId, date) {
  const response = await fetch(`${API_BASE}/reconciliation/${clinicId}/${date}`);
  if (!response.ok) throw new Error('Reconciliation not found');
  return response.json();
}

export async function getAnalytics(clinicId, date) {
  const response = await fetch(`${API_BASE}/analytics/${clinicId}/${date}`);
  if (!response.ok) throw new Error('Analytics not found');
  return response.json();
}

export async function getNarrative(clinicId, date) {
  const response = await fetch(`${API_BASE}/narrative/${clinicId}/${date}`);
  if (!response.ok) throw new Error('Narrative not found');
  return response.json();
}

/**
 * Format paise to rupee display string.
 */
export function formatPaise(paise) {
  const rupees = Math.abs(paise) / 100;
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: rupees % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(rupees);
  return paise < 0 ? `-${formatted}` : formatted;
}

/**
 * Format hour (0-23) to display string.
 */
export function formatHour(hour) {
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${displayHour}:00 ${period}`;
}
