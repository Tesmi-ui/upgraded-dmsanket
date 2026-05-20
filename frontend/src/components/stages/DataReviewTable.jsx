import React, { useState, useEffect } from 'react';
import { useMigration } from '../../contexts/MigrationContext';

export default function DataReviewTable() {
    const { api, jobId, setStatus } = useMigration();
    const [changes, setChanges] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    
    // Track user edits: { [rowIndex]: { gender: "Male", category: "SC" } }
    const [edits, setEdits] = useState({});

    useEffect(() => {
        let mounted = true;
        api.getSuggestions(jobId).then(data => {
            if (mounted) {
                // The backend selectively filters changes based on advisoryCols
                const filtered = data.changes || [];
                setChanges(filtered);
                setLoading(false);
            }
        }).catch(err => {
            console.error("Failed to load suggestions:", err);
            if (mounted) setLoading(false);
        });
        return () => { mounted = false; };
    }, [jobId, api]);

    const handleEditChange = (rowIndex, field, value) => {
        setEdits(prev => ({
            ...prev,
            [rowIndex]: {
                ...(prev[rowIndex] || {}),
                [field]: value
            }
        }));
    };

    const handleSave = async () => {
        setSaving(true);
        // Flatten edits dictionary into array
        const payload = [];
        Object.entries(edits).forEach(([rowStr, fieldEdits]) => {
            const rowIndex = parseInt(rowStr, 10);
            Object.entries(fieldEdits).forEach(([field, value]) => {
                payload.push({ row_index: rowIndex, field: field, value: value });
            });
        });

        try {
            if (payload.length > 0) {
                await api.applyEdits(jobId, payload);
            }
            alert(`Review complete! ${payload.length} manual edits applied.`);
            
            // Re-fetch status to clear the review block or let the user click proceed.
            // Actually just setting a local state flag so we can unblock the proceed button later
            setChanges([]); 
        } catch (err) {
            alert('Failed to apply edits: ' + err.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-4 text-center">Loading suggestions...</div>;
    if (changes.length === 0) return null; // Hide if no valid suggestions to review

    return (
        <div className="card mt-4" style={{ borderColor: 'var(--accent)'}}>
            <div className="card-header">
                <div className="card-title-group">
                    <div className="card-icon">👀</div>
                    <div>
                        <div className="card-title">Review & Edit Data</div>
                        <div className="card-subtitle">Manually review the flagged items before proceeding</div>
                    </div>
                </div>
            </div>
            
            <div className="overflow-x-auto" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                <table className="table w-full" style={{ minWidth: '800px', textAlign: 'left', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead style={{ position: 'sticky', top: 0, backgroundColor: 'var(--surface)', zIndex: 1, borderBottom: '1px solid var(--border)' }}>
                        <tr>
                            <th style={{ padding: '0.75rem' }}>Row</th>
                            <th style={{ padding: '0.75rem' }}>Farmer / Father</th>
                            <th style={{ padding: '0.75rem' }}>Field</th>
                            <th style={{ padding: '0.75rem' }}>Original (Bad)</th>
                            <th style={{ padding: '0.75rem' }}>Suggested Fix</th>
                            <th style={{ padding: '0.75rem' }}>Your Edit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {changes.map((change, idx) => {
                            // Backend row_num corresponds to Excel_Row. Pandas drops 2 offset for header indexing.
                            const backendRowIndex = change.Excel_Row - 2; 
                            const field = change.Field;
                            const currentEdit = edits[backendRowIndex]?.[field] ?? change.New_Value;

                            return (
                                <tr key={idx} style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
                                    <td style={{ padding: '0.75rem' }}>{change.Excel_Row}</td>
                                    <td style={{ padding: '0.75rem' }}>
                                        <strong>{change.Farmer_Name}</strong><br/>
                                        <span style={{ color: 'var(--text-muted)' }}>{change.Father_Spouse}</span>
                                    </td>
                                    <td style={{ padding: '0.75rem', textTransform: 'capitalize' }}>
                                        <span className="system-feature-tag">{field}</span>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem'}}>{change.Reason?.split('→')[0] || change.Method}</div>
                                    </td>
                                    <td style={{ padding: '0.75rem', color: 'var(--error)' }}>
                                        <del>{change.Old_Value || '(empty)'}</del>
                                    </td>
                                    <td style={{ padding: '0.75rem', color: 'var(--success)' }}>
                                        {change.New_Value}
                                        <div style={{ fontSize: '0.7rem' }}>{change["Confidence_%"]}% conf</div>
                                    </td>
                                    <td style={{ padding: '0.75rem' }}>
                                        {field === 'gender' ? (
                                            <select 
                                                className="select" 
                                                style={{ width: '120px', padding: '0.5rem' }}
                                                value={currentEdit}
                                                onChange={e => handleEditChange(backendRowIndex, field, e.target.value)}
                                            >
                                                <option value="male">Male</option>
                                                <option value="female">Female</option>
                                                <option value="others">Others</option>
                                            </select>
                                        ) : field === 'category' ? (
                                            <select 
                                                className="select" 
                                                style={{ width: '120px', padding: '0.5rem' }}
                                                value={currentEdit}
                                                onChange={e => handleEditChange(backendRowIndex, field, e.target.value)}
                                            >
                                                <option value="gen">GEN</option>
                                                <option value="obc">OBC</option>
                                                <option value="sc">SC</option>
                                                <option value="st">ST</option>
                                                <option value="sbc">SBC</option>
                                                <option value="pvtg">PVTG</option>
                                            </select>
                                        ) : (
                                            <input 
                                                type="text" 
                                                className="input"
                                                style={{ padding: '0.5rem' }}
                                                value={currentEdit}
                                                onChange={e => handleEditChange(backendRowIndex, field, e.target.value)}
                                            />
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            <div style={{ padding: '1rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
                <button 
                    className="btn btn-primary" 
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Saving...' : 'Approve & Apply Edits ✓'}
                </button>
            </div>
        </div>
    );
}
