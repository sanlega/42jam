import React from 'react';
import './StatusPanel.css';

function StatusPanel({ health, power, currentDay, messagesSent, messagesPerDay }) {
  return (
    <div className="status-panel">
      <h2>Status</h2>
      <div className="status-item">
        <strong>Health:</strong>
        <div className="status-bar">
          <div className="status-fill health" style={{ width: `${health}%` }}></div>
        </div>
        <span>{health}</span>
      </div>
      <div className="status-item">
        <strong>Power:</strong>
        <div className="status-bar">
          <div className="status-fill power" style={{ width: `${power}%` }}></div>
        </div>
        <span>{power}</span>
      </div>
      <div className="status-item">
        <strong>Day:</strong>
        <span>{currentDay}</span>
      </div>
      <div className="status-item">
        <strong>Messages Sent:</strong>
        <span>{messagesSent}/{messagesPerDay}</span>
      </div>
    </div>
  );
}

export default StatusPanel;
