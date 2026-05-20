import React, { createContext, useContext, useState, useRef, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import { useJobPolling } from '../hooks/useJobPolling';

const MigrationContext = createContext();

export const useMigration = () => {
  return useContext(MigrationContext);
};

export const MigrationProvider = ({ children }) => {
  const api = useApi();

  // Stage Management
  const [currentStage, setCurrentStage] = useState(1);
  const [completedStages, setCompletedStages] = useState([]);

  // File Management
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // System Selection
  const [selectedSystem, setSelectedSystem] = useState('production');

  // Processing Options
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState({
    autoCorrect: true,
    removeDupes: true,
    spellCheck: true,
    minConfidence: 75,
    validateSchema: true,
    checkCompliance: true,
    dryRun: false,
    auditTrail: true,
    notify: false,
  });

  // Job State
  const [jobId, setJobId] = useState(null);
  const [processing, setProcessing] = useState(false);

  // Modeling State (Stage 2)
  const [selectedFormat, setSelectedFormat] = useState('nrm');

  // Migration State (Stage 3)
  const [migrationStatus, setMigrationStatus] = useState('pending');
  const [uploadProgress] = useState(0);

  const handlePollComplete = useCallback((data) => {
    setProcessing(false);
    if (currentStage === 1) {
      setCompletedStages(prev => [...new Set([...prev, 1])]);
    }
  }, [currentStage]);

  const handlePollError = useCallback(() => {
    setProcessing(false);
  }, []);

  const { status, setStatus, reset: resetStatus } = useJobPolling(
    jobId, processing, handlePollComplete, handlePollError
  );

  const handleReset = () => {
    setFile(null);
    setUploadResult(null);
    setJobId(null);
    resetStatus();
    setProcessing(false);
    setCurrentStage(1);
    setCompletedStages([]);
    setSelectedSystem('production');
    setSelectedFormat('nrm');
    setMigrationStatus('pending');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDownload = async (fileType) => {
    try {
      await api.download(jobId, fileType);
    } catch {
      alert(`Download failed for "${fileType}"`);
    }
  };

  const handleStageClick = (stageId) => {
    if (stageId <= Math.max(...completedStages, 0) + 1) {
      setCurrentStage(stageId);
    }
  };

  const handleProceed = () => {
    if (currentStage < 3) {
      setCompletedStages(prev => [...new Set([...prev, currentStage])]);
      setCurrentStage(currentStage + 1);
    }
  };

  const value = {
    api,
    currentStage, setCurrentStage,
    completedStages, setCompletedStages,
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
    selectedFormat, setSelectedFormat,
    migrationStatus, setMigrationStatus,
    uploadProgress,
    status, setStatus, resetStatus,
    handleReset, handleDownload, handleProceed, handleStageClick
  };

  return (
    <MigrationContext.Provider value={value}>
      {children}
    </MigrationContext.Provider>
  );
};
