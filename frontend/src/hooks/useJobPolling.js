/**
 * useJobPolling — Extracted polling logic for job status tracking.
 */
import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

export function useJobPolling(jobId, isPolling, onComplete, onError) {
    const { getStatus } = useApi();
    const [status, setStatus] = useState(null);

    useEffect(() => {
        if (!jobId || !isPolling) return;

        const pollInterval = setInterval(async () => {
            try {
                const data = await getStatus(jobId);
                setStatus(data);

                if (data.status === 'complete' || data.status === 'complete_with_errors') {
                    onComplete?.(data);
                } else if (data.status === 'error') {
                    onError?.(data);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 2000);

        return () => clearInterval(pollInterval);
    }, [jobId, isPolling, getStatus, onComplete, onError]);

    const reset = useCallback(() => setStatus(null), []);

    return { status, setStatus, reset };
}

export default useJobPolling;
