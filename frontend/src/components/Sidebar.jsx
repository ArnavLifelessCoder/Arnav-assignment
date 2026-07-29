import { useState, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { uploadBillingLog } from '../api/client';

export default function Sidebar({ reports, selectedReport, onSelectReport, onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadStatus(null);

    try {
      const result = await uploadBillingLog(file);
      setUploadStatus({
        type: 'success',
        message: `Processed ${result.records_processed} records` +
          (result.records_rejected > 0 ? `, ${result.records_rejected} skipped` : ''),
      });
      onUploadComplete?.(result);
    } catch (err) {
      setUploadStatus({ type: 'error', message: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.json')) {
      handleUpload(file);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">S</div>
          <span className="sidebar-brand">SwasthiQ</span>
        </div>
        <div className="sidebar-subtitle">EOD Analytics Agent</div>
      </div>

      {selectedReport && (
        <div className="clinic-info">
          <div className="clinic-name">Mehta Multi-Specialty Clinic</div>
          <div className="clinic-id">{selectedReport.clinic_id}</div>
        </div>
      )}

      <nav className="sidebar-nav">
        <div className="sidebar-section-title">Dashboard</div>
        <NavLink to="/reconciliation" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor"><path d="M2 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1H3a1 1 0 01-1-1V4zm6 2a1 1 0 011-1h2a1 1 0 011 1v10a1 1 0 01-1 1H9a1 1 0 01-1-1V6zm6-4a1 1 0 011-1h2a1 1 0 011 1v14a1 1 0 01-1 1h-2a1 1 0 01-1-1V2z"/></svg>
          Reconciliation
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11 4a1 1 0 10-2 0v4a1 1 0 102 0V7zm-3 1a1 1 0 10-2 0v3a1 1 0 102 0V8zM8 9a1 1 0 00-2 0v2a1 1 0 102 0V9z" clipRule="evenodd"/></svg>
          Analytics
        </NavLink>
        <NavLink to="/narrative" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd"/></svg>
          AI Summary
        </NavLink>
      </nav>

      {reports.length > 0 && (
        <div className="date-selector">
          <label>Report Date</label>
          <select
            className="date-select"
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

      <div className="upload-area">
        <div
          className={`upload-dropzone ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <svg className="upload-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
          </svg>
          <div className="upload-text">
            <strong>Upload</strong> billing log
          </div>
          <div className="upload-hint">Drop .json or click to browse</div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => handleUpload(e.target.files[0])}
          />
        </div>

        {uploading && (
          <div className="upload-progress">
            <div className="upload-status">Processing...</div>
            <div className="upload-progress-bar">
              <div className="upload-progress-fill" style={{ width: '60%' }} />
            </div>
          </div>
        )}

        {uploadStatus && (
          <div className="upload-progress">
            <div className={`upload-status ${uploadStatus.type}`}>
              {uploadStatus.message}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
