import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HeaderNav from './components/HeaderNav';
import ReconciliationDashboard from './components/ReconciliationDashboard';
import AnalyticsPage from './components/AnalyticsPage';
import NarrativePage from './components/NarrativePage';
import { listReports, getFullReport } from './api/client';
import './index.css';

export default function App() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReports = useCallback(async () => {
    try {
      const data = await listReports();
      setReports(data);
      if (data.length > 0 && !selectedReport) {
        setSelectedReport({ clinic_id: data[0].clinic_id, date: data[0].date });
      }
    } catch (err) {
      console.log('No reports available yet');
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  useEffect(() => {
    if (!selectedReport) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getFullReport(selectedReport.clinic_id, selectedReport.date);
        setReportData(data);
      } catch (err) {
        setError(err.message);
        setReportData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedReport]);

  const handleUploadComplete = (result) => {
    fetchReports();
    if (result.clinic_id && result.date) {
      setSelectedReport({ clinic_id: result.clinic_id, date: result.date });
    }
    if (result.reconciliation && result.analytics) {
      setReportData({
        reconciliation: result.reconciliation,
        analytics: result.analytics,
        narrative: result.narrative,
      });
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="loading-state">
          <div className="loading-spinner" />
          <p>Loading Billing Records...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="empty-state-card">
          <h3>Error Loading Data</h3>
          <p>{error}</p>
        </div>
      );
    }

    return (
      <Routes>
        <Route
          path="/reconciliation"
          element={<ReconciliationDashboard data={reportData?.reconciliation} />}
        />
        <Route
          path="/analytics"
          element={<AnalyticsPage data={reportData?.analytics} reconData={reportData?.reconciliation} />}
        />
        <Route
          path="/narrative"
          element={<NarrativePage data={reportData?.narrative} />}
        />
        <Route path="*" element={<Navigate to="/reconciliation" replace />} />
      </Routes>
    );
  };

  return (
    <BrowserRouter>
      <div className="app-wrapper">
        <HeaderNav
          reports={reports}
          selectedReport={selectedReport}
          reportData={reportData}
          onSelectReport={setSelectedReport}
          onUploadComplete={handleUploadComplete}
        />
        <main className="main-container">
          {renderContent()}
        </main>
      </div>
    </BrowserRouter>
  );
}
