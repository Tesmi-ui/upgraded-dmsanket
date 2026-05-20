import React from 'react';
import Toggle from '../Toggle';
import { useMigration } from '../../contexts/MigrationContext';
import { formatNumber } from '../../utils/formatters';

export default function Stage2Model() {
  const {
    api,
    options, setOptions,
    jobId, processing, setProcessing,
    status, setStatus,
    selectedFormat, setSelectedFormat,
    setCurrentStage, handleProceed, handleDownload
  } = useMigration();

  const handleProcess = async () => {
    if (!jobId) return;
    setProcessing(true);
    setStatus(null);

    try {
      const requestData = {
        job_id: jobId,
        stage: 2,
        options: {
          ...options,
          modeling_options: {
            target_format: selectedFormat,
            validate_compliance: options.checkCompliance,
          }
        },
      };

      await api.process(jobId, requestData);
    } catch (err) {
      alert('Processing failed: ' + err.message);
      setProcessing(false);
    }
  };

  const isComplete = status?.status === 'complete';

  return (
    <>
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <div className="card-icon">🔄</div>
            <div>
              <div className="card-title">Data Modeling & Transformation</div>
              <div className="card-subtitle">Map to target formats (NRM, Govt Schemas)</div>
            </div>
          </div>
          <div className="card-badge">Stage 2</div>
        </div>

        <div className="system-selector" style={{ marginBottom: '1.5rem' }}>
          {[
            { key: 'nrm', icon: '📋', title: 'NRM Format', desc: 'National Resource Management standard format for government reporting', tags: ['Govt Compliant', 'Standardized'] },
            { key: 'pmkisan', icon: '🌾', title: 'PM-KISAN Schema', desc: 'Pradhan Mantri Kisan Samman Nidhi specific data structure format', tags: ['Aadhaar Linked', 'Beneficiary'] },
            { key: 'custom', icon: '⚙️', title: 'Custom Mapping', desc: 'Define custom field mappings and transformation rules', tags: ['Flexible', 'Configurable'] },
          ].map(fmt => (
            <div key={fmt.key} className={`system-option ${selectedFormat === fmt.key ? 'selected' : ''}`} onClick={() => setSelectedFormat(fmt.key)}>
              <label className="system-option-content">
                <input type="radio" name="format" value={fmt.key} checked={selectedFormat === fmt.key} onChange={(e) => setSelectedFormat(e.target.value)} />
                <div className="system-option-header">
                  <div className="system-icon">{fmt.icon}</div>
                  <div className="system-title">{fmt.title}</div>
                </div>
                <div className="system-desc">{fmt.desc}</div>
                <div className="system-features">
                  {fmt.tags.map(t => <span key={t} className="system-feature-tag">{t}</span>)}
                </div>
              </label>
            </div>
          ))}
        </div>

        <div className="modeling-preview">
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Field Mapping Preview
          </div>
          <table className="mapping-table">
            <thead>
              <tr><th>Source Field</th><th>→</th><th>Target Field</th><th>Status</th></tr>
            </thead>
            <tbody>
              {[
                ['farmer_name', 'beneficiary_name', true],
                ['aadhaar_number', 'uid', true],
                ['mobile_no', 'contact_number', false],
                ['bank_account', 'account_no', true],
                ['ifsc_code', 'ifsc', true],
              ].map(([src, tgt, mapped]) => (
                <tr key={src}>
                  <td>{src}</td>
                  <td style={{ color: 'var(--accent-primary)' }}>→</td>
                  <td>{tgt}</td>
                  <td>
                    <span className={`mapping-status ${mapped ? 'mapped' : 'pending'}`}>
                      {mapped ? '✓ Mapped' : '⏳ Pending'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="options-panel" style={{ marginTop: '1.5rem' }}>
          <div className="option-row">
            <div className="option-info">
              <div className="option-label">Validate Compliance</div>
              <div className="option-hint">Check against schema requirements</div>
            </div>
            <Toggle checked={options.checkCompliance} onChange={(v) => setOptions({ ...options, checkCompliance: v })} />
          </div>
          <div className="option-row">
            <div className="option-info">
              <div className="option-label">Auto-fix Invalid Data</div>
              <div className="option-hint">Apply corrections during transformation</div>
            </div>
            <Toggle checked={options.autoCorrect} onChange={(v) => setOptions({ ...options, autoCorrect: v })} />
          </div>
          <div className="option-row">
            <div className="option-info">
              <div className="option-label">Generate Transformation Report</div>
              <div className="option-hint">Detailed log of all changes made</div>
            </div>
            <Toggle checked={options.validateSchema} onChange={(v) => setOptions({ ...options, validateSchema: v })} />
          </div>
        </div>

        <div className="btn-group" style={{ marginTop: '1.5rem' }}>
          <button className="btn btn-primary btn-lg" onClick={handleProcess} disabled={processing}>
            {processing ? (<><span className="spinner" /> Transforming...</>) : (<>Apply Transformation →</>)}
          </button>
          <button className="btn btn-secondary" onClick={() => setCurrentStage(1)}>← Back</button>
        </div>

        {isComplete && (
          <div className="alert alert-success" style={{ marginTop: '1rem' }}>
            <span className="alert-icon">✓</span>
            <div><strong>Transformation complete!</strong> Data mapped to {selectedFormat.toUpperCase()} format.</div>
          </div>
        )}
      </div>

      {isComplete && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon">📊</div>
              <div>
                <div className="card-title">Transformation Results</div>
                <div className="card-subtitle">Summary of changes applied</div>
              </div>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{formatNumber(status?.stats?.fields_mapped)}</div>
              <div className="stat-label">Fields Mapped</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{formatNumber(status?.stats?.records_transformed || status?.stats?.final_records)}</div>
              <div className="stat-label">Records Transformed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{formatNumber(status?.stats?.compliance_checks)}</div>
              <div className="stat-label">Compliance Checks</div>
            </div>
            <div className="stat-card highlight">
              <div className="stat-value">✓</div>
              <div className="stat-label">Schema Valid</div>
            </div>
          </div>

          <div className="download-section" style={{ marginTop: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '1rem', fontWeight: 600 }}>
              Download Transformed Files
            </div>
            <div className="download-grid">
              <div className="download-card" onClick={() => handleDownload('transformed')}>
                <div className="download-icon">🔄</div>
                <div className="download-title">Transformed Data</div>
                <div className="download-meta">{selectedFormat.toUpperCase()} format</div>
              </div>
              <div className="download-card" onClick={() => handleDownload('mapping_report')}>
                <div className="download-icon">🗺️</div>
                <div className="download-title">Mapping Report</div>
                <div className="download-meta">Field transformations</div>
              </div>
              <div className="download-card" onClick={() => handleDownload('compliance_report')}>
                <div className="download-icon">✅</div>
                <div className="download-title">Compliance Report</div>
                <div className="download-meta">Validation results</div>
              </div>
            </div>
          </div>

          <button className="btn btn-primary btn-full btn-lg" onClick={handleProceed} style={{ marginTop: '1.5rem' }}>
            Proceed to Migration →
          </button>
        </div>
      )}
    </>
  );
}
