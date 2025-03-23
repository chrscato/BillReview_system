"""
Flask web application for rate validation failure analysis.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import tempfile
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.parser import ValidationFailureParser
from analyzer.aggregator import RateFailureAggregator
from analyzer.reporter import ReportGenerator
from analyzer.ppo_updater import PPOUpdater

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure file paths
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'rate_validator_uploads'
OUTPUT_FOLDER = Path(tempfile.gettempdir()) / 'rate_validator_output'
ALLOWED_EXTENSIONS = {'json'}

# Default database path
DEFAULT_DB_PATH = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\reference_tables\orders2.db")

# Create directories if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['DB_PATH'] = DEFAULT_DB_PATH

# Cache for analysis results
analysis_cache = {
    'timestamp': None,
    'summary': None,
    'failures_df': None,
    'report_paths': None
}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_default_log_dir():
    """Get the default validation logs directory."""
    return Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\validation logs")

def find_latest_validation_file(search_dir=None):
    """Find the latest validation failures JSON file."""
    if search_dir is None:
        search_dir = get_default_log_dir()
    
    json_files = list(search_dir.glob('*validation_failures*.json'))
    
    if not json_files:
        return None
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    return json_files[0]

@app.route('/', methods=['GET'])
def index():
    """Render the home page."""
    latest_file = find_latest_validation_file()
    latest_file_info = {
        'name': latest_file.name if latest_file else 'No file found',
        'path': str(latest_file) if latest_file else None,
        'modified': datetime.fromtimestamp(latest_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S') if latest_file else None
    }
    
    return render_template(
        'index.html', 
        latest_file=latest_file_info,
        has_analysis=analysis_cache['summary'] is not None
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    # If the user does not select a file
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = app.config['UPLOAD_FOLDER'] / filename
        file.save(file_path)
        
        # Process the uploaded file
        return redirect(url_for('analyze', file_path=file_path))
    
    flash('Invalid file type. Please upload a JSON file.')
    return redirect(url_for('index'))

@app.route('/analyze')
def analyze():
    """Analyze a validation failures file."""
    file_path = request.args.get('file_path')
    use_latest = request.args.get('use_latest', 'false') == 'true'
    
    if use_latest:
        file_path = find_latest_validation_file()
        if not file_path:
            flash('No validation files found')
            return redirect(url_for('index'))
    elif not file_path:
        flash('No file specified')
        return redirect(url_for('index'))
    
    file_path = Path(file_path)
    if not file_path.exists():
        flash(f'File not found: {file_path}')
        return redirect(url_for('index'))
    
    print(f"Analyzing file: {file_path}")
    
    # Parse validation failures
    parser = ValidationFailureParser()
    if not parser.load_file(file_path):
        flash(f'Failed to load file: {file_path}')
        return redirect(url_for('index'))
    
    # Check that we have a valid JSON array
    if not isinstance(parser.raw_data, list):
        flash(f'Invalid file format: Expected a JSON array but got {type(parser.raw_data).__name__}')
        return redirect(url_for('index'))
    
    # Extract rate failures
    print(f"Extracting rate validation failures from {len(parser.raw_data)} records...")
    rate_failures = parser.extract_rate_failures()
    
    if not rate_failures:
        flash('No rate validation failures found in the file. Check if it contains rate validation entries.')
        return redirect(url_for('index'))
    
    print(f"Found {len(rate_failures)} rate validation failures")
    
    # Convert to DataFrame
    print("Converting to DataFrame...")
    failures_df = parser.to_dataframe()
    
    if failures_df.empty:
        flash('Failed to convert rate failures to DataFrame')
        return redirect(url_for('index'))
    
    # Show dataframe info
    print(f"DataFrame info: {len(failures_df)} rows, {len(failures_df.columns)} columns")
    print(f"DataFrame columns: {', '.join(failures_df.columns)}")
    
    # Analyze failures
    print("Analyzing failures...")
    aggregator = RateFailureAggregator(failures_df)
    summary = aggregator.analyze()
    
    # Generate reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Generating reports with timestamp: {timestamp}")
    reporter = ReportGenerator(failures_df, summary)
    reporter.set_output_directory(app.config['OUTPUT_FOLDER'])
    report_paths = reporter.generate_all_reports(timestamp)
    
    # Cache results for later access
    analysis_cache['timestamp'] = timestamp
    analysis_cache['summary'] = summary
    analysis_cache['failures_df'] = failures_df
    analysis_cache['report_paths'] = report_paths
    
    print("Analysis complete, redirecting to dashboard")
    # Redirect to dashboard
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Display analysis results dashboard."""
    if analysis_cache['summary'] is None:
        flash('No analysis available. Please analyze a file first.')
        return redirect(url_for('index'))
    
    return render_template(
        'dashboard.html',
        summary=analysis_cache['summary'],
        timestamp=analysis_cache['timestamp'],
        report_paths=analysis_cache['report_paths']
    )

@app.route('/update_rates')
def update_rates():
    """Display rate update options."""
    # Check if we have analysis data
    has_failures = analysis_cache['failures_df'] is not None and not analysis_cache['failures_df'].empty
    failure_count = len(analysis_cache['failures_df']) if has_failures else 0
    
    # Get all procedure categories
    categories = PPOUpdater.get_all_categories()
    
    # Check if we have update results in session
    update_result = session.pop('update_result', None)
    
    return render_template(
        'update_rates.html',
        has_failures=has_failures,
        failure_count=failure_count,
        categories=categories,
        update_result=update_result
    )

@app.route('/update_rates/from_failures', methods=['POST'])
def update_rates_from_failures():
    """Update rates based on current failure data."""
    # Check if we have analysis data
    if analysis_cache['failures_df'] is None or analysis_cache['failures_df'].empty:
        flash('No analysis data available. Please analyze a file first.')
        return redirect(url_for('update_rates'))
    
    # Get form data
    default_rate = float(request.form.get('defaultRate', 500.00))
    state = request.form.get('state', 'XX')
    
    # Initialize PPO updater
    updater = PPOUpdater(app.config['DB_PATH'])
    
    # Update rates
    success, report = updater.update_rates_from_failures(
        analysis_cache['failures_df'],
        default_rate=default_rate,
        state=state
    )
    
    # Store result in session for display
    session['update_result'] = {
        'success': success,
        'message': f"Updated {report['updated']} rates, {report['failed']} failed" if success else "Failed to update rates",
        'details': report['details']
    }
    
    return redirect(url_for('update_rates'))

@app.route('/update_rates/category', methods=['POST'])
def update_category_rates():
    """Update rates by category."""
    # Get form data
    state = request.form.get('state', '')
    tin = request.form.get('tin', '')
    provider_name = request.form.get('provider_name', '')
    
    # Get category rates
    category_rates = {}
    for category in PPOUpdater.get_all_categories():
        rate_key = f"rate_{category.replace(' ', '_').replace('/', '_')}"
        rate_str = request.form.get(rate_key, '')
        
        if rate_str:
            try:
                rate = float(rate_str)
                category_rates[category] = rate
            except ValueError:
                pass
    
    # Check if we have any rates
    if not category_rates:
        flash('No valid rates provided.')
        return redirect(url_for('update_rates'))
    
    # Initialize PPO updater
    updater = PPOUpdater(app.config['DB_PATH'])
    
    # Update rates
    success, message = updater.update_rate_by_category(
        state=state,
        tin=tin,
        provider_name=provider_name,
        category_rates=category_rates
    )
    
    # Store result in session for display
    session['update_result'] = {
        'success': success,
        'message': message
    }
    
    return redirect(url_for('update_rates'))

@app.route('/update_rates/individual', methods=['POST'])
def update_individual_rate():
    """Update an individual rate."""
    # Get form data
    state = request.form.get('state', '')
    tin = request.form.get('tin', '')
    provider_name = request.form.get('provider_name', '')
    proc_cd = request.form.get('proc_cd', '')
    modifier = request.form.get('modifier', '')
    
    try:
        rate = float(request.form.get('rate', 0))
    except ValueError:
        flash('Invalid rate value.')
        return redirect(url_for('update_rates'))
    
    # Initialize PPO updater
    updater = PPOUpdater(app.config['DB_PATH'])
    
    # Update rate
    success, message = updater.update_single_rate(
        state=state,
        tin=tin,
        provider_name=provider_name,
        proc_cd=proc_cd,
        modifier=modifier,
        rate=rate
    )
    
    # Store result in session for display
    session['update_result'] = {
        'success': success,
        'message': message
    }
    
    return redirect(url_for('update_rates'))

@app.route('/api/summary')
def api_summary():
    """Return analysis summary as JSON."""
    if analysis_cache['summary'] is None:
        return jsonify({'error': 'No analysis available'})
    
    return jsonify(analysis_cache['summary'])

@app.route('/api/providers')
def api_providers():
    """Return provider analysis as JSON."""
    if analysis_cache['summary'] is None:
        return jsonify({'error': 'No analysis available'})
    
    return jsonify(analysis_cache['summary'].get('unique_providers', {}))

@app.route('/api/cpts')
def api_cpts():
    """Return CPT analysis as JSON."""
    if analysis_cache['summary'] is None:
        return jsonify({'error': 'No analysis available'})
    
    return jsonify(analysis_cache['summary'].get('cpt_analysis', {}))

@app.route('/api/failures')
def api_failures():
    """Return rate failures as JSON."""
    if analysis_cache['failures_df'] is None:
        return jsonify({'error': 'No analysis available'})
    
    return jsonify(analysis_cache['failures_df'].to_dict(orient='records'))

@app.route('/download/<report_type>')
def download_report(report_type):
    """Download a generated report."""
    if analysis_cache['report_paths'] is None:
        flash('No reports available. Please analyze a file first.')
        return redirect(url_for('index'))
    
    if report_type not in analysis_cache['report_paths']:
        flash(f'Report not found: {report_type}')
        return redirect(url_for('dashboard'))
    
    report_path = analysis_cache['report_paths'][report_type]
    
    return send_file(
        report_path,
        as_attachment=True,
        download_name=report_path.name
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)