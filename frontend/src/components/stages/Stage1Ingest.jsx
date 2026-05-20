import React, { useState } from 'react';
import Toggle from '../Toggle';
import { useMigration } from '../../contexts/MigrationContext';
import { formatNumber, formatFileSize } from '../../utils/formatters';
import DataReviewTable from './DataReviewTable';

export default function Stage1Ingest() {
  const {
    api,
    file, setFile,
    dragging, setDragging,
    fileInputRef,
    uploading, setUploading,
    uploadResult, setUploadResult,
    selectedSystem, setSelectedSystem,
    showOptions, setShowOptions,
    options, setOptions,
    jobId, setJobId,
    processing, setProcessing,
    status, setStatus, resetStatus,
    handleReset, handleDownload, handleProceed,
    setCompletedStages
  } = useMigration();

  const [advisoryCols, setAdvisoryCols] = useState(['farmer_name', 'gender', 'category']);

  const handleToggleCol = (colStr) => {
    setAdvisoryCols(prev => prev.includes(colStr) 
      ? prev.filter(c => c !== colStr) 
      : [...prev, colStr]
    );
  };

  // ── File Handlers ────────────────────────────────────────────────────

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) validateAndSetFile(droppedFile);
  };

  const validateAndSetFile = (selectedFile) => {
    const ext = selectedFile.name.split('.').pop().toLowerCase();
    const allowed = ['xlsx', 'xls', 'csv', 'tsv'];

    if (!allowed.includes(ext)) {
      alert(`Unsupported format ".${ext}". Supported: ${allowed.join(', ')}`);
      return;
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      alert('File size exceeds 100MB limit');
      return;
    }

    setFile(selectedFile);
    setUploadResult(null);
    setJobId(null);
    resetStatus();
    setCompletedStages([]);
  };

  const handleFileSelect = (e) => {
    if (e.target.files[0]) validateAndSetFile(e.target.files[0]);
  };

  // ── Upload Handler ───────────────────────────────────────────────────

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);

    try {
      const data = await api.upload(file);
      setUploadResult(data);
      setJobId(data.job_id);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  // ── Process Handler ──────────────────────────────────────────────────

  const handleProcess = async () => {
    if (!jobId) return;
    setProcessing(true);
    setStatus(null);

    try {
      const requestData = {
        job_id: jobId,
        system: selectedSystem,
        stage: 1,
        options: {
          ...options,
          production_options: selectedSystem === 'production' ? {
            unique_key: 'Unique Key',
            farmer_col: 'farmer_name',
            father_col: 'father_spouse_name',
            submission_date: 'SubmissionDate',
            remove_duplicates: options.removeDupes,
            auto_correct: options.autoCorrect,
            correct_fields: ['gender', 'category'],
            min_confidence: options.minConfidence,
            spell_enabled: options.spellCheck,
          } : null,
          check_options: ['global', 'advisory'].includes(selectedSystem) ? {
            mode: selectedSystem.toUpperCase(),
            dry_run: false,
            selected_columns: advisoryCols,
            selected_rules: ['auto_correct', 'auto_correct_gender', 'auto_correct_category', 'infer_gender', 'infer_category', 'spell_check'] 
          } : null,
        },
      };

      await api.process(jobId, requestData);
    } catch (err) {
      alert('Processing failed: ' + err.message);
      setProcessing(false);
    }
  };

  const isComplete = status?.status === 'complete';
  const isError = status?.status === 'error';
  const schemaErrors = uploadResult?.schema_errors || [];
  const schemaWarnings = uploadResult?.schema_warnings || [];

  return (
    <>
      {/* Upload Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <div className="card-icon">📂</div>
            <div>
              <div className="card-title">Data Ingestion</div>
              <div className="card-subtitle">Upload source files for processing</div>
            </div>
          </div>
          <div className="card-badge">Stage 1</div>
        </div>

        <div className="upload-container">
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv,.tsv"
              disabled={uploading || processing}
              onChange={handleFileSelect}
            />
            <span className="upload-icon-large">☁️</span>
            <div className="upload-title">Drop files here or click to browse</div>
            <div className="upload-hint">Supports XLSX, XLS, CSV, TSV • Max 100MB</div>
          </div>

          {file && (
            <div className="file-preview">
              <div className="file-icon">📄</div>
              <div className="file-details">
                <div className="file-name">{file.name}</div>
                <div className="file-meta">
                  <span>{formatFileSize(file.size)}</span>
                  <span>•</span>
                  <span>{file.type || 'Unknown type'}</span>
                </div>
              </div>
              <button className="file-remove" onClick={() => setFile(null)} disabled={uploading} title="Remove file">
                ✕
              </button>
            </div>
          )}
        </div>

        {(schemaErrors.length > 0 || schemaWarnings.length > 0) && (
          <div className="validation-panel">
            <div className="validation-header">⚡ Validation Results</div>
            <div className="validation-list">
              {schemaErrors.map((error, idx) => (
                <div key={idx} className="validation-item error">
                  <span className="validation-icon">🚫</span>
                  <div className="validation-content">
                    <div className="validation-field">{error.field || error.type}</div>
                    <div className="validation-message">{error.message}</div>
                  </div>
                </div>
              ))}
              {schemaWarnings.map((warning, idx) => (
                <div key={idx} className="validation-item warning">
                  <span className="validation-icon">⚠️</span>
                  <div className="validation-content">
                    <div className="validation-field">{warning.field || warning.type}</div>
                    <div className="validation-message">{warning.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="btn-group" style={{ marginTop: '1.5rem' }}>
          <button className="btn btn-primary btn-lg" onClick={handleUpload} disabled={!file || uploading || !!uploadResult}>
            {uploading ? (<><span className="spinner" /> Uploading...</>) : (<>Upload & Validate →</>)}
          </button>
          {uploadResult && (
            <button className="btn btn-secondary" onClick={handleReset}>Reset</button>
          )}
        </div>

        {uploadResult && !processing && !status && (
          <div className="alert alert-success">
            <span className="alert-icon">✓</span>
            <div><strong>Upload successful!</strong> Job ID: {uploadResult.job_id}</div>
          </div>
        )}
      </div>

      {/* System Selection */}
      {uploadResult && !isComplete && !isError && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon">⚙️</div>
              <div>
                <div className="card-title">Processing Configuration</div>
                <div className="card-subtitle">Select data cleaning methodology</div>
              </div>
            </div>
          </div>

          <div className="system-selector">
            {[
              { key: 'production', icon: '🏭', title: 'Production Pipeline', desc: 'Full data cleansing with deduplication, auto-correction, and comprehensive audit reporting', tags: ['Deduplication', 'Auto-correct', '9-Sheet Report'] },
              { key: 'global', icon: '🌍', title: 'Check Intelligence (Global)', desc: 'Automated corrections across all fields with strict gender library validation', tags: ['Auto-fix', 'High Confidence', 'Batch Process'] },
              { key: 'advisory', icon: '💡', title: 'Check Intelligence (Advisory)', desc: 'Review mode - flags potential issues without modifying source data', tags: ['Suggestions', 'Safe Mode', 'Review Ready'] },
            ].map(sys => (
              <div key={sys.key} className={`system-option ${selectedSystem === sys.key ? 'selected' : ''}`} onClick={() => setSelectedSystem(sys.key)}>
                <label className="system-option-content">
                  <input type="radio" name="system" value={sys.key} checked={selectedSystem === sys.key} onChange={(e) => setSelectedSystem(e.target.value)} />
                  <div className="system-option-header">
                    <div className="system-icon">{sys.icon}</div>
                    <div className="system-title">{sys.title}</div>
                  </div>
                  <div className="system-desc">{sys.desc}</div>
                  <div className="system-features">
                    {sys.tags.map(tag => <span key={tag} className="system-feature-tag">{tag}</span>)}
                  </div>
                </label>
              </div>
            ))}
          </div>

          {selectedSystem === 'production' && (
            <div className="options-panel" style={{ marginTop: '1.5rem' }}>
              <div className="options-header" onClick={() => setShowOptions(!showOptions)}>
                <span className="options-title">{showOptions ? '▼' : '▶'} Advanced Options</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{showOptions ? 'Hide' : 'Show'}</span>
              </div>

              {showOptions && (
                <>
                  <div className="option-row">
                    <div className="option-info">
                      <div className="option-label">Auto-correct Fields</div>
                      <div className="option-hint">Gender, category, mobile, MGNREGA ID</div>
                    </div>
                    <Toggle checked={options.autoCorrect} onChange={(v) => setOptions({ ...options, autoCorrect: v })} />
                  </div>
                  <div className="option-row">
                    <div className="option-info">
                      <div className="option-label">Remove Duplicates</div>
                      <div className="option-hint">Keep first occurrence per unique key</div>
                    </div>
                    <Toggle checked={options.removeDupes} onChange={(v) => setOptions({ ...options, removeDupes: v })} />
                  </div>
                  <div className="option-row">
                    <div className="option-info">
                      <div className="option-label">Spell Check Names</div>
                      <div className="option-hint">Phonetic + fuzzy matching</div>
                    </div>
                    <Toggle checked={options.spellCheck} onChange={(v) => setOptions({ ...options, spellCheck: v })} />
                  </div>
                  <div className="option-row">
                    <div className="option-info">
                      <div className="option-label">Minimum Confidence</div>
                      <div className="option-hint">Threshold for auto-corrections</div>
                    </div>
                    <select className="select" value={options.minConfidence} onChange={(e) => setOptions({ ...options, minConfidence: Number(e.target.value) })}>
                      {[50, 60, 70, 75, 80, 85, 90, 95].map(v => <option key={v} value={v}>{v}%</option>)}
                    </select>
                  </div>
                </>
              )}
            </div>
          )}

          {selectedSystem !== 'production' && (
            <>
              <div className="options-panel" style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--surface2)', borderRadius: '8px' }}>
                <div style={{ marginBottom: '1rem', fontWeight: 600 }}>Select Columns to Check</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                  {[
                    { val: 'farmer_name', label: 'Farmer Name' },
                    { val: 'gender', label: 'Gender' },
                    { val: 'category', label: 'Category' },
                    { val: 'village', label: 'Village' },
                    { val: 'district', label: 'District' },
                    { val: 'contact_number', label: 'Contact Output' }
                  ].map(c => (
                    <label key={c.val} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={advisoryCols.includes(c.val)}
                        onChange={() => handleToggleCol(c.val)} 
                      />
                      {c.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="alert alert-info" style={{ marginTop: '1rem' }}>
                <span className="alert-icon">ℹ️</span>
                <div>
                  {selectedSystem === 'global'
                    ? 'Global mode applies automatic corrections with ≥80% confidence threshold'
                    : 'Advisory mode generates suggestion reports without modifying your data'}
                </div>
              </div>
            </>
          )}

          <button className="btn btn-primary btn-full btn-lg" onClick={handleProcess} disabled={processing} style={{ marginTop: '1.5rem' }}>
            {processing ? (<><span className="spinner spinner-light" /> Processing...</>) : (<>Start Processing →</>)}
          </button>
        </div>
      )}

      {/* Progress & Results */}
      {status && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <div className="card-icon">📊</div>
              <div>
                <div className="card-title">
                  {isComplete ? 'Processing Complete' : isError ? 'Processing Error' : 'Processing...'}
                </div>
                <div className="card-subtitle">
                  {status.system_used && `System: ${status.system_used.toUpperCase()}`}
                </div>
              </div>
            </div>
            {isComplete && <div className="card-badge" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>✓ Done</div>}
          </div>

          {!isError && (
            <div className="progress-container">
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${status.progress || 0}%` }} />
              </div>
              <div className="progress-meta">
                <div className="progress-percentage">{status.progress || 0}%</div>
                <div className="progress-status">{status.message}</div>
              </div>
            </div>
          )}

          {isError && (
            <div className="alert alert-error">
              <span className="alert-icon">🚫</span>
              <div>{status.message}</div>
            </div>
          )}

          {isComplete && status.stats && (
            <>
              <div className="stats-grid">
                {selectedSystem === 'production' ? (
                  <>
                    <div className="stat-card">
                      <div className="stat-value">{formatNumber(status.stats.original_records)}</div>
                      <div className="stat-label">Original Records</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{formatNumber(status.stats.duplicates_removed)}</div>
                      <div className="stat-label">Duplicates Removed</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{formatNumber(status.stats.auto_corrections)}</div>
                      <div className="stat-label">Auto Corrections</div>
                    </div>
                    <div className="stat-card highlight">
                      <div className="stat-value">{formatNumber(status.stats.final_records)}</div>
                      <div className="stat-label">Clean Records</div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="stat-card">
                      <div className="stat-value">{formatNumber(status.stats.total_records)}</div>
                      <div className="stat-label">Total Records</div>
                    </div>
                    <div className="stat-card highlight">
                      <div className="stat-value">{formatNumber(status.stats.corrections_made || status.stats.issues_found)}</div>
                      <div className="stat-label">{selectedSystem === 'global' ? 'Corrections Made' : 'Issues Flagged'}</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{formatNumber(status.stats.suggestions_flagged)}</div>
                      <div className="stat-label">Suggestions</div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-value">{status.stats.mode_used || selectedSystem.toUpperCase()}</div>
                      <div className="stat-label">Mode</div>
                    </div>
                  </>
                )}
              </div>

              <div className="download-section">
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '1rem', fontWeight: 600 }}>
                  Download Results
                </div>
                <div className="download-grid">
                  {selectedSystem === 'production' ? (
                    <>
                      <div className="download-card" onClick={() => handleDownload('cleaned')}>
                        <div className="download-icon">🧹</div>
                        <div className="download-title">Cleaned Data</div>
                        <div className="download-meta">All corrections applied</div>
                      </div>
                      <div className="download-card" onClick={() => handleDownload('merged')}>
                        <div className="download-icon">⚡</div>
                        <div className="download-title">Merged Dataset</div>
                        <div className="download-meta">Deduplicated records</div>
                      </div>
                      <div className="download-card" onClick={() => handleDownload('review')}>
                        <div className="download-icon">👁️</div>
                        <div className="download-title">Review Report</div>
                        <div className="download-meta">Highlighted changes</div>
                      </div>
                      <div className="download-card" onClick={() => handleDownload('report')}>
                        <div className="download-icon">📋</div>
                        <div className="download-title">Audit Report</div>
                        <div className="download-meta">9-sheet workbook</div>
                      </div>
                    </>
                  ) : (
                    <div className="download-card" onClick={() => handleDownload('checked')}>
                      <div className="download-icon">✅</div>
                      <div className="download-title">Processed File</div>
                      <div className="download-meta">
                        {selectedSystem === 'global' ? 'With corrections applied' : 'With suggestions flagged'}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {['global', 'advisory'].includes(selectedSystem) && <DataReviewTable />}

              <button className="btn btn-primary btn-full btn-lg" onClick={handleProceed} style={{ marginTop: '1.5rem' }}>
                Proceed to Modeling →
              </button>
            </>
          )}
        </div>
      )}
    </>
  );
}
