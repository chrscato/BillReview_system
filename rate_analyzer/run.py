"""
Main entry point for the rate validation failure analyzer.
"""
import os
import sys
from pathlib import Path
import json
import argparse
from datetime import datetime

from analyzer.parser import ValidationFailureParser
from analyzer.aggregator import RateFailureAggregator
from analyzer.reporter import ReportGenerator

def find_latest_validation_file(search_dir: Path) -> Path:
    """
    Find the latest validation failures JSON file in the directory.
    
    Args:
        search_dir: Directory to search in
        
    Returns:
        Path: Path to the latest validation failures JSON file
    """
    json_files = list(search_dir.glob('*validation_failures*.json'))
    
    if not json_files:
        raise FileNotFoundError(f"No validation failure files found in {search_dir}")
    
    # Sort by modification time (newest first)
    json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    return json_files[0]

def analyze_failures(input_file: Path, output_dir: Path) -> dict:
    """
    Analyze rate validation failures from a JSON file.
    
    Args:
        input_file: Path to the JSON file containing validation failures
        output_dir: Directory to save reports to
        
    Returns:
        dict: Analysis results and report paths
    """
    # Create timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Parse validation failures
    parser = ValidationFailureParser()
    if not parser.load_file(input_file):
        return {"error": f"Failed to load file: {input_file}"}
    
    # Check that we have a valid JSON array
    if not isinstance(parser.raw_data, list):
        return {"error": f"Invalid file format: Expected a JSON array but got {type(parser.raw_data).__name__}"}
    
    # Extract rate failures
    print(f"Extracting rate validation failures from {len(parser.raw_data)} records...")
    rate_failures = parser.extract_rate_failures()
    
    if not rate_failures:
        return {"error": "No rate validation failures found in the file. Check if it contains rate validation entries."}
    
    print(f"Found {len(rate_failures)} rate validation failures")
    
    # Convert to DataFrame
    print("Converting to DataFrame...")
    failures_df = parser.to_dataframe()
    
    if failures_df.empty:
        return {"error": "Failed to convert rate failures to DataFrame"}
    
    # Show dataframe info
    print(f"DataFrame info: {len(failures_df)} rows, {len(failures_df.columns)} columns")
    print(f"DataFrame columns: {', '.join(failures_df.columns)}")
    
    # Analyze failures
    print("Analyzing failures...")
    aggregator = RateFailureAggregator(failures_df)
    summary = aggregator.analyze()
    
    # Generate reports
    print(f"Generating reports with timestamp: {timestamp}")
    reporter = ReportGenerator(failures_df, summary)
    reporter.set_output_directory(output_dir)
    report_paths = reporter.generate_all_reports(timestamp)
    
    print("Analysis complete!")
    return {
        "analysis": summary,
        "report_paths": report_paths,
        "failure_count": len(rate_failures),
        "timestamp": timestamp
    }

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze rate validation failures")
    parser.add_argument(
        "-i", "--input",
        help="Path to the validation failures JSON file"
    )
    parser.add_argument(
        "-d", "--directory",
        help="Directory containing validation failures JSON files (uses latest if -i not provided)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Directory to save reports to (default: ./output)"
    )
    
    args = parser.parse_args()
    
    # Determine input file
    input_file = None
    if args.input:
        input_file = Path(args.input)
        if not input_file.exists():
            print(f"Error: Input file not found: {input_file}")
            return 1
    elif args.directory:
        try:
            input_file = find_latest_validation_file(Path(args.directory))
        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            return 1
    else:
        # Default behavior: look in the 'validation logs' directory
        default_log_dir = Path(r"C:\Users\ChristopherCato\OneDrive - clarity-dx.com\Documents\Bill_Review_INTERNAL\validation logs")
        try:
            input_file = find_latest_validation_file(default_log_dir)
        except FileNotFoundError as e:
            print(f"Error: {str(e)}")
            print("Please specify an input file with -i or a directory with -d")
            return 1
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Analyze failures
    print(f"Analyzing rate validation failures from: {input_file}")
    print(f"Saving reports to: {output_dir}")
    
    results = analyze_failures(input_file, output_dir)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        return 1
    
    # Print summary
    print("\nAnalysis complete!")
    print(f"Found {results['failure_count']} rate validation failures")
    print("\nReports generated:")
    for report_type, report_path in results['report_paths'].items():
        print(f"- {report_type}: {report_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())