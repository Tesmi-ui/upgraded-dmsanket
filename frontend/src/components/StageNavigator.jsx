/**
 * StageNavigator — Pipeline stage progress indicator.
 */
import React from 'react';

const STAGES = [
    { id: 1, label: 'Ingest & Clean', desc: 'Upload & validate' },
    { id: 2, label: 'Model & Map', desc: 'Format transformation' },
    { id: 3, label: 'Migrate', desc: 'Deploy & upload' },
];

export default function StageNavigator({ currentStage, completedStages, onStageClick }) {
    return (
        <div className="stage-nav">
            {STAGES.map((stage, index) => {
                const isActive = currentStage === stage.id;
                const isCompleted = completedStages.includes(stage.id);
                const isDisabled = stage.id > currentStage && !isCompleted;

                return (
                    <React.Fragment key={stage.id}>
                        <div
                            className={`stage-nav-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isDisabled ? 'disabled' : ''}`}
                            onClick={() => !isDisabled && onStageClick(stage.id)}
                        >
                            <div className="stage-number">
                                {isCompleted ? '✓' : stage.id}
                            </div>
                            <div className="stage-info">
                                <div className="stage-label">{stage.label}</div>
                                <div className="stage-desc">{stage.desc}</div>
                            </div>
                        </div>
                        {index < STAGES.length - 1 && (
                            <div className="stage-connector">→</div>
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}
