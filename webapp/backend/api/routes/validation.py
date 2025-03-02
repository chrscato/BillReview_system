from flask import Blueprint, jsonify, request
from api.services.validation_service import ValidationService

validation_routes = Blueprint('validation', __name__)
validation_service = ValidationService()

@validation_routes.route('/sessions', methods=['GET'])
def get_validation_sessions():
    """Get all validation sessions."""
    sessions = validation_service.get_all_sessions()
    return jsonify(sessions)

@validation_routes.route('/sessions/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get details for a specific validation session."""
    session = validation_service.get_session_details(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session)

@validation_routes.route('/sessions/<session_id>/failures', methods=['GET'])
def get_session_failures(session_id):
    """Get all failures for a specific validation session."""
    failures = validation_service.get_session_failures(session_id)
    return jsonify(failures)

@validation_routes.route('/failures/<failure_id>/correction', methods=['POST'])
def submit_correction(failure_id):
    """Submit a correction for a validation failure."""
    correction_data = request.json
    result = validation_service.process_correction(failure_id, correction_data)
    return jsonify(result)

@validation_routes.route('/stats/common-errors', methods=['GET'])
def get_common_errors():
    """Get statistics about common validation errors."""
    stats = validation_service.get_error_statistics()
    return jsonify(stats)

@validation_routes.route('/compare/<file_id>', methods=['GET'])
def compare_versions(file_id):
    """Compare original and corrected versions of a file."""
    comparison = validation_service.compare_versions(file_id)
    return jsonify(comparison) 