import pytest
from pathlib import Path
from api.services.validation_service import ValidationService

@pytest.fixture
def validation_service(tmp_path):
    """Create a ValidationService instance with a temporary log directory."""
    service = ValidationService()
    service.log_dir = tmp_path
    return service

def test_get_all_sessions(validation_service, tmp_path):
    """Test retrieving all validation sessions."""
    # Copy test data to temp directory
    test_data = Path(__file__).parent / 'test_data/validation_summary_20240301_120000.json'
    if test_data.exists():
        import shutil
        shutil.copy(test_data, tmp_path)

    sessions = validation_service.get_all_sessions()
    assert len(sessions) > 0
    assert 'session_id' in sessions[0]
    assert 'timestamp' in sessions[0]
    assert 'total_files' in sessions[0]

def test_get_session_failures(validation_service, tmp_path):
    """Test retrieving failures for a specific session."""
    # Copy test data to temp directory
    test_data = Path(__file__).parent / 'test_data/validation_failures_20240301_120000.json'
    if test_data.exists():
        import shutil
        shutil.copy(test_data, tmp_path)

    failures = validation_service.get_session_failures('test-session-1')
    assert len(failures) > 0
    assert 'file_info' in failures[0]
    assert 'validation_summary' in failures[0]
    assert 'failure_details' in failures[0]

def test_process_correction(validation_service):
    """Test processing a correction submission."""
    correction_data = {
        'modifier': 'LT',
        'notes': 'Correcting modifier from RT to LT'
    }
    
    result = validation_service.process_correction('test-file-1', correction_data)
    assert result['status'] == 'success'
    assert 'correction_id' in result

def test_get_error_statistics(validation_service, tmp_path):
    """Test generating error statistics."""
    # Copy test data to temp directory
    test_data = Path(__file__).parent / 'test_data/validation_failures_20240301_120000.json'
    if test_data.exists():
        import shutil
        shutil.copy(test_data, tmp_path)

    stats = validation_service.get_error_statistics()
    assert 'error_codes' in stats
    assert 'severity_levels' in stats
    assert 'validation_types' in stats
    assert 'total_failures' in stats 