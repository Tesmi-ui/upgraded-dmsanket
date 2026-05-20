/**
 * Toggle — Reusable toggle switch component.
 */
import React from 'react';

export default function Toggle({ checked, onChange, disabled = false }) {
    return (
        <label className={`toggle ${disabled ? 'disabled' : ''}`}>
            <input
                type="checkbox"
                checked={checked}
                onChange={(e) => onChange(e.target.checked)}
                disabled={disabled}
            />
            <span className="toggle-track" />
        </label>
    );
}
