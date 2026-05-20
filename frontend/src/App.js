// App.js — DMS Data Migration System v5.0
// Lean orchestrator — components and hooks extracted to separate modules.
import React from 'react';
import './App.css';

// Components
import StageNavigator from './components/StageNavigator';
import ErrorBoundary from './components/ErrorBoundary';

// Context
import { MigrationProvider, useMigration } from './contexts/MigrationContext';

// Stages
import Stage1Ingest from './components/stages/Stage1Ingest';
import Stage2Model from './components/stages/Stage2Model';
import Stage3Migrate from './components/stages/Stage3Migrate';

function AppContent() {
  const { currentStage, completedStages, handleStageClick, api } = useMigration();

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="header-logo">DMS</div>
          <div className="header-title-group">
            <div className="header-title">DMS Data Migration System</div>
            <div className="header-subtitle">Enterprise Data Management Platform</div>
          </div>
        </div>
        <div className="header-meta">
          <div className="connection-status">
            <span className="status-dot"></span>
            <span>System Online</span>
          </div>
          <div className="version-badge">v5.0</div>
        </div>
      </header>

      <main className="main">
        <StageNavigator
          currentStage={currentStage}
          completedStages={completedStages}
          onStageClick={handleStageClick}
        />

        {currentStage === 1 && <Stage1Ingest />}
        {currentStage === 2 && <Stage2Model />}
        {currentStage === 3 && <Stage3Migrate />}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-brand">
          <div className="footer-logo">DMS</div>
          <div className="footer-text">© 2026 DMS Data Migration System. All rights reserved.</div>
        </div>
        <nav className="footer-links">
          <a className="footer-link" href="/nrm_auto_mapper.html" target="_blank" rel="noreferrer" style={{color: '#00e5a0'}}>
            <span>⚡</span> NRM Auto Mapper
          </a>
          <a className="footer-link" href="/cross_file_checker.html" target="_blank" rel="noreferrer" style={{color: '#4f8ef7'}}>
            <span>🔍</span> Data Checker
          </a>
          <div style={{width: '1px', height: '14px', background: 'var(--border)', margin: '0 8px'}}></div>
          <a className="footer-link" href={`${api.API_URL}/docs`} target="_blank" rel="noreferrer">
            <span>📚</span> API Docs
          </a>
          <a className="footer-link" href={`${api.API_URL}/health`} target="_blank" rel="noreferrer">
            <span>💓</span> System Health
          </a>
          <a className="footer-link" href="#support" onClick={(e) => { e.preventDefault(); alert('Support: support@dms-enterprise.com'); }}>
            <span>🎧</span> Support
          </a>
        </nav>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <MigrationProvider>
        <AppContent />
      </MigrationProvider>
    </ErrorBoundary>
  );
}