/**
 * useApi — Centralized API client hook with error handling.
 *
 * Features:
 * - Base URL configuration from environment
 * - Consistent error handling with user-friendly messages
 * - Optional API key header injection
 * - Request timeout support
 */
import { useCallback } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_KEY = process.env.REACT_APP_API_KEY || '';

export function useApi() {
    const request = useCallback(async (path, options = {}) => {
        const headers = { ...options.headers };

        if (API_KEY) {
            headers['X-API-Key'] = API_KEY;
        }

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), options.timeout || 120000);

        try {
            const res = await fetch(`${API_URL}${path}`, {
                ...options,
                headers,
                signal: controller.signal,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Request failed (${res.status})`);
            }

            return res;
        } catch (err) {
            if (err.name === 'AbortError') {
                throw new Error('Request timed out — server may be busy');
            }
            throw err;
        } finally {
            clearTimeout(timeout);
        }
    }, []);

    const upload = useCallback(async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        const res = await request('/api/upload', {
            method: 'POST',
            body: formData,
        });
        return res.json();
    }, [request]);

    const process = useCallback(async (jobId, data) => {
        const res = await request(`/api/process/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    }, [request]);

    const getStatus = useCallback(async (jobId) => {
        const res = await request(`/api/status/${jobId}`);
        return res.json();
    }, [request]);

    const download = useCallback(async (jobId, fileType) => {
        const res = await request(`/api/download/${jobId}/${fileType}`);

        const contentDisposition = res.headers.get('content-disposition') || '';
        const match = contentDisposition.match(/filename="?([^";\n]+)"?/);
        const filename = match ? match[1] : `${fileType}_${jobId}.xlsx`;

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    }, [request]);

    const migrate = useCallback(async (jobId, data) => {
        const res = await request(`/api/migrate/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return res.json();
    }, [request]);

    const getSuggestions = useCallback(async (jobId) => {
        const res = await request(`/api/jobs/${jobId}/suggestions`);
        return res.json();
    }, [request]);

    const applyEdits = useCallback(async (jobId, edits) => {
        const res = await request(`/api/jobs/${jobId}/apply-edits`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ edits }),
        });
        return res.json();
    }, [request]);

    return { API_URL, upload, process, getStatus, download, migrate, getSuggestions, applyEdits, request };
}

export default useApi;
