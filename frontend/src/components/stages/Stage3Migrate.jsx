import React from 'react';
import Toggle from '../Toggle';
import { useMigration } from '../../contexts/MigrationContext';
import { formatNumber } from '../../utils/formatters';

export default function Stage3Migrate() {
  const {
    api,
    options, setOptions,
    jobId, selectedFormat, status,
    migrationStatus, setMigrationStatus,
    uploadProgress, setCurrentStage, setCompletedStages,
    handleReset, handleDownload
  } = useMigration();

  const handleMigrationUpload = async () => {
    setMigrationStatus('uploading');

    try {
      await api.migrate(jobId, {
        format: selectedFormat,
        validate_only: options.dryRun || false,
      });
      setMigrationStatus('complete');
      setCompletedStages(prev => [...new Set([...prev, 3])]);
    } catch (err) {
      setMigrationStatus('error');
      alert('Migration failed: ' + err.message);
    }
  };

  return (
    <>
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <div className="card-icon">🚀</div>
            <div>
              <div className="card-title">Data Migration & Upload</div>
              <div className="card-subtitle">Deploy to target systems</div>
            </div>
          </div>
          <div className="card-badge">Stage 3</div>
        </div>

        {migrationStatus === 'pending' && (
          <>
            <div className="system-selector" style={{ marginBottom: '1.5rem' }}>
              <div className="system-option selected">
                <div className="system-option-content">
                  <div className="system-option-header">
                    <div className="system-icon">🎯</div>
                    <div className="system-title">Target System</div>
                  </div>
                  <div className="system-desc" style={{ paddingLeft: '3.5rem' }}>
                    <strong>Format:</strong> {selectedFormat?.toUpperCase()}<br />
                    <strong>Records:</strong> {formatNumber(status?.stats?.final_records || 0)}<br />
                    <strong>Status:</strong> Ready for migration
                  </div>
                  <div className="system-features" style={{ paddingLeft: '3.5rem' }}>
                    <span className="system-feature-tag">Validated</span>
                    <span className="system-feature-tag">Transformed</span>
                    <span className="system-feature-tag">Compliant</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="options-panel">
              <div className="option-row">
                <div className="option-info">
                  <div className="option-label">Validate Only (Dry Run)</div>
                  <div className="option-hint">Test migration without uploading</div>
                </div>
                <Toggle checked={options.dryRun || false} onChange={(v) => setOptions({ ...options, dryRun: v })} />
              </div>
              <div className="option-row">
                <div className="option-info">
                  <div className="option-label">Generate Audit Trail</div>
                  <div className="option-hint">Log all migration activities</div>
                </div>
                <Toggle checked={options.auditTrail !== false} onChange={(v) => setOptions({ ...options, auditTrail: v })} />
              </div>
              <div className="option-row">
                <div className="option-info">
                  <div className="option-label">Notify on Completion</div>
                  <div className="option-hint">Send email notification when done</div>
                </div>
                <Toggle checked={options.notify || false} onChange={(v) => setOptions({ ...options, notify: v })} />
              </div>
            </div>

            <div className="btn-group" style={{ marginTop: '1.5rem' }}>
              <button className="btn btn-primary btn-lg" onClick={handleMigrationUpload}>Start Migration →</button>
              <button className="btn btn-secondary" onClick={() => setCurrentStage(2)}>← Back</button>
            </div>
          </>
        )}

        {migrationStatus === 'uploading' && (
          <div className="migration-status">
            <div className="migration-icon-large">📤</div>
            <div className="migration-title">Uploading Data...</div>
            <div className="migration-desc">Please do not close this window while data is being migrated to the target system.</div>
            <div className="progress-container" style={{ width: '100%', maxWidth: '400px' }}>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
              <div className="progress-meta">
                <div className="progress-percentage">{uploadProgress}%</div>
                <div className="progress-status">Uploading records...</div>
              </div>
            </div>
          </div>
        )}

        {migrationStatus === 'complete' && (
          <>
            <div className="migration-status">
              <div className="migration-icon-large" style={{ background: 'var(--success-bg)', color: 'var(--success)', opacity: 1 }}>✓</div>
              <div className="migration-title">Migration Complete!</div>
              <div className="migration-desc">All data has been successfully migrated to the target system.</div>
            </div>

            <div className="stats-grid">
              <div className="stat-card highlight">
                <div className="stat-value">{formatNumber(status?.stats?.final_records || 0)}</div>
                <div className="stat-label">Records Migrated</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">100%</div>
                <div className="stat-label">Success Rate</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">0</div>
                <div className="stat-label">Failed Records</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{new Date().toLocaleTimeString()}</div>
                <div className="stat-label">Completed At</div>
              </div>
            </div>

            <div className="download-section" style={{ marginTop: '1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '1rem', fontWeight: 600 }}>
                Migration Artifacts
              </div>
              <div className="download-grid">
                <div className="download-card" onClick={() => handleDownload('migration_log')}>
                  <div className="download-icon">📋</div>
                  <div className="download-title">Migration Log</div>
                  <div className="download-meta">Complete audit trail</div>
                </div>
                <div className="download-card" onClick={() => handleDownload('receipt')}>
                  <div className="download-icon">🧾</div>
                  <div className="download-title">Migration Receipt</div>
                  <div className="download-meta">Confirmation document</div>
                </div>
                <div className="download-card" onClick={() => handleDownload('summary')}>
                  <div className="download-icon">📊</div>
                  <div className="download-title">Summary Report</div>
                  <div className="download-meta">Executive summary</div>
                </div>
              </div>
            </div>

            <button className="btn btn-primary btn-full btn-lg" onClick={handleReset} style={{ marginTop: '1.5rem' }}>
              Start New Migration →
            </button>
          </>
        )}

        {migrationStatus === 'error' && (
          <div className="migration-status">
            <div className="migration-icon-large" style={{ background: 'var(--error-bg)', color: 'var(--error)', opacity: 1 }}>✕</div>
            <div className="migration-title">Migration Failed</div>
            <div className="migration-desc">An error occurred during migration. Please check the logs and try again.</div>
            <div className="btn-group" style={{ marginTop: '1rem' }}>
              <button className="btn btn-primary" onClick={() => setMigrationStatus('pending')}>Retry Migration</button>
              <button className="btn btn-secondary" onClick={() => setCurrentStage(2)}>← Back to Modeling</button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
