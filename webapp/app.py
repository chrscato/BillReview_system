from flask import Flask, render_template, jsonify, send_from_directory
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__, template_folder='templates', static_folder='static')

def load_validation_data():
    """Load validation data from JSON files in the logs directory"""
    logs_dir = Path('logs')
    summaries = {}
    failures = {}
    
    # Load summaries
    for summary_file in logs_dir.glob('validation_summary_*.json'):
        with open(summary_file) as f:
            data = json.load(f)
            session_id = data.get('session_id')
            if session_id:
                summaries[session_id] = data
    
    # Load failures
    for failure_file in logs_dir.glob('validation_failures_*.json'):
        with open(failure_file) as f:
            data = json.load(f)
            session_id = data.get('session_id')
            if session_id:
                failures[session_id] = data
    
    return summaries, failures

@app.route('/')
def index():
    """Main page showing validation sessions"""
    summaries, _ = load_validation_data()
    return render_template('index.html', sessions=summaries.values())

@app.route('/session/<session_id>')
def session_details(session_id):
    """Page showing details for a specific session"""
    summaries, failures = load_validation_data()
    session_summary = summaries.get(session_id, {})
    session_failures = failures.get(session_id, {})
    return render_template('session.html', 
                         summary=session_summary, 
                         failures=session_failures)

@app.route('/api/sessions')
def get_sessions():
    """API endpoint for getting all sessions"""
    summaries, _ = load_validation_data()
    return jsonify(list(summaries.values()))

@app.route('/api/sessions/<session_id>/failures')
def get_session_failures(session_id):
    """API endpoint for getting failures for a specific session"""
    _, failures = load_validation_data()
    session_failures = failures.get(session_id, {})
    return jsonify(session_failures)

@app.route('/api/stats/common-errors')
def get_error_stats():
    """API endpoint for getting error statistics"""
    _, failures = load_validation_data()
    error_stats = {
        'error_codes': {},
        'severity_levels': {},
        'validation_types': {}
    }
    
    for session_failures in failures.values():
        for failure in session_failures.get('failures', []):
            error_code = failure.get('error_code', 'UNKNOWN')
            severity = failure.get('severity', 'UNKNOWN')
            val_type = failure.get('validation_type', 'UNKNOWN')
            
            error_stats['error_codes'][error_code] = error_stats['error_codes'].get(error_code, 0) + 1
            error_stats['severity_levels'][severity] = error_stats['severity_levels'].get(severity, 0) + 1
            error_stats['validation_types'][val_type] = error_stats['validation_types'].get(val_type, 0) + 1
    
    return jsonify(error_stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 