import { useState, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { uploadBillingLog } from '../api/client';
import { exportReportToCSV } from '../utils/exportCsv';

export default function HeaderNav({ reports, selectedReport, reportData, onSelectReport, onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadStatus(null);

    try {
      const result = await uploadBillingLog(file);
      setUploadStatus({
        type: 'success',
        message: `Processed ${result.records_processed} records successfully`,
      });
      onUploadComplete?.(result);
    } catch (err) {
      setUploadStatus({ type: 'error', message: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        {/* Brand Logo & Clinic Info */}
        <div className="top-nav-brand">
          <div className="brand-logo-mark">
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="36" height="36" rx="10" fill="url(#brand-grad)"/>
              <path d="M10 12C10 10.8954 10.8954 10 12 10H20C21.1046 10 22 10.8954 22 12V24C22 25.1046 21.1046 26 20 26H12C10.8954 26 10 25.1046 10 24V12Z" stroke="white" strokeWidth="2" strokeLinejoin="round"/>
              <path d="M14 14H18" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <path d="M14 18H18" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <path d="M14 22H16" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <circle cx="23" cy="21" r="5" fill="#10B981"/>
              <path d="M21 21L22.5 22.5L25 19.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="brand-grad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#1D4ED8"/>
                  <stop offset="1" stopColor="#3B82F6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div>
            <div className="brand-title">Kaagazy Billing</div>
            <div className="brand-subtitle">Mehta Multi-Specialty Clinic · {selectedReport?.clinic_id || 'CLN-KNP-014'}</div>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="top-nav-tabs">
          <NavLink to="/reconciliation" className={({ isActive }) => `tab-link ${isActive ? 'active' : ''}`}>
            Reconciliation
          </NavLink>
          <NavLink to="/analytics" className={({ isActive }) => `tab-link ${isActive ? 'active' : ''}`}>
            Analytics
          </NavLink>
          <NavLink to="/narrative" className={({ isActive }) => `tab-link ${isActive ? 'active' : ''}`}>
            Executive Brief
          </NavLink>
        </nav>

        {/* Controls: Date Picker, Export CSV & Upload Button */}
        <div className="top-nav-actions">
          {reports.length > 0 && (
            <div className="header-date-picker">
              <span className="date-picker-label">Date</span>
              <select
                className="header-date-select"
                value={selectedReport ? `${selectedReport.clinic_id}|${selectedReport.date}` : ''}
                onChange={(e) => {
                  const [cid, date] = e.target.value.split('|');
                  onSelectReport?.({ clinic_id: cid, date });
                }}
              >
                {reports.map((r) => (
                  <option key={`${r.clinic_id}-${r.date}`} value={`${r.clinic_id}|${r.date}`}>
                    {r.date}
                  </option>
                ))}
              </select>
            </div>
          )}

          {reportData && (
            <button
              className="export-btn"
              onClick={() => exportReportToCSV(reportData)}
              title="Export Report to CSV / Excel"
            >
              <svg className="btn-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/>
              </svg>
              Export CSV
            </button>
          )}

          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <svg className="btn-icon" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd"/>
            </svg>
            {uploading ? 'Processing...' : 'Upload Log'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => handleUpload(e.target.files[0])}
          />
        </div>
      </div>

      {uploadStatus && (
        <div className={`top-nav-toast ${uploadStatus.type}`}>
          {uploadStatus.message}
        </div>
      )}
    </header>
  );
}
