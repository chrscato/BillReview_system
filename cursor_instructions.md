# Cursor AI Prompt Engineering Guide
## Bill Validation System Improvement Project

This guide provides structured prompts for implementing improvements to the medical bill validation system using Cursor AI. We'll approach this in multiple phases to make the implementation manageable.

## Using This Guide

1. Copy the prompt for the specific task you're working on
2. Adjust the prompt based on your current file context and specific needs
3. Paste the prompt into Cursor AI
4. Review, refine, and integrate the generated code

---

## Phase 1: Enhanced Error Classification and Reporting

### Task 1.1: Create Error Manager Class

```
Create a new file called "core/services/error_manager.py" that implements an error classification and prioritization system for our bill validation failures. 

The class should:
1. Define error severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFO)
2. Define error categories (billing, coding, bundle, rate, format)
3. Support lookup of error details from error codes (e.g., MOD_001, RATE_001)
4. Include a priority scoring method that considers:
   - Error severity
   - Financial impact (based on charge amounts)
   - Provider network status (in-network vs. out-of-network)

Include a default configuration for our common error codes:
- MOD_001: Invalid modifier combination (Medium severity, Coding category)
- UNIT_001: Invalid unit count (High severity, Coding category)
- RATE_001: Rate mismatch (High severity, Rate category)
- BNDL_001: Bundle configuration error (Medium severity, Bundle category)
- LINE_001: Line item mismatch (Medium severity, Coding category)

Each error should include recommended resolution steps.

Use the existing code structure and follow our project's coding style.
```

### Task 1.2: Enhance Validation Logger

```
Modify our existing core/services/logger.py to create an enhanced logger that supports:

1. Logging all validation results regardless of pass/fail status
2. Capturing detailed context for each validation step
3. Generating comprehensive reports with:
   - Overall validation statistics
   - Detailed failure information
   - Prioritized lists of issues to fix
   - Resolution suggestions

Make it compatible with our existing code but add new methods for:
- log_validation_step(): Log each validation step with its result and context
- generate_file_report(): Create a detailed report for a single file
- generate_session_report(): Create a report for an entire validation session

Ensure it can work with the error_manager.py we created to enrich failure records with severity and resolution information.

Use our existing coding patterns and error-handling approach.
```

### Task 1.3: Update Validation Flow

```
Modify main.py to implement a "complete validation" mode that continues processing all validation steps even when failures are found.

Instead of returning after the first validation failure, update the process_file() method to:
1. Run all validation steps (modifier, units, bundle, line items, rate)
2. Collect results from each step
3. Log each step using our enhanced logger
4. Only mark a file as failed after all validations have run

Add a configuration option (settings.COMPLETE_VALIDATION) to toggle between fail-fast and complete validation modes.

Keep the existing validation logic, just change the flow to support collecting all errors before finishing.
```

---

## Phase 2: Resolution Tracking System 

### Task 2.1: Create Database Models

```
Create a new file called "core/models/resolution.py" that defines SQLAlchemy models for tracking validation failures and their resolution.

Include these models:
1. ValidationFailure: Stores details about each validation failure
   - id, session_id, file_name, order_id, patient_name
   - validation_type, error_code, error_message
   - status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED)
   - priority, assigned_to, resolution_notes, timestamps

2. ResolutionAction: Tracks actions taken to resolve failures
   - id, failure_id (foreign key)
   - action_type (NOTE, STATUS_CHANGE, ASSIGNMENT)
   - action_value, created_by, timestamp

Follow SQLAlchemy conventions and our existing model patterns. Include appropriate methods for serialization to dictionaries.
```

### Task 2.2: Create Resolution Database Service

```
Create a new file called "core/services/resolution_db.py" that provides an interface for storing and retrieving resolution data.

Implement these functions:
1. initialize_db(): Create database and tables if they don't exist
2. import_failures(): Import validation failures from our JSON log files
3. update_failure_status(): Update the status of a failure
4. assign_failure(): Assign a failure to a user
5. add_resolution_note(): Add a note to a failure's resolution history
6. get_failures(): Get failures with filtering options
7. get_failure_details(): Get detailed information about a specific failure
8. get_resolution_stats(): Get statistics about failures and resolutions

Use SQLite for simplicity and SQLAlchemy for ORM. Ensure proper error handling and transaction management.
```

### Task 2.3: Create Simple Console Resolution Tool

```
Create a script called "tools/resolution_console.py" that provides a command-line interface for managing failure resolutions.

Implement these features:
1. Import failures from a validation log file
2. List failures with filtering by status, type, priority
3. View details of a specific failure
4. Update failure status
5. Add resolution notes
6. Export resolution reports

Use argparse for command-line argument handling and create a simple menu-driven interface when run without arguments.

This should be a lightweight tool that uses the resolution_db.py service for data access.
```

---

## Phase 3: Advanced Features

### Task 3.1: Implement Batch Processing

```
Create a file called "tools/batch_processor.py" that implements batch processing for common failure types.

The tool should:
1. Accept a validation failures JSON file as input
2. Identify patterns of common failures
3. Suggest batch resolutions for similar failures
4. Allow applying the same resolution to multiple failures
5. Update the resolution database accordingly

Focus on these common scenarios:
- Rate errors for the same provider
- Modifier issues with the same CPT code
- Line item mismatches of the same type

Use our existing services and follow our coding patterns. Include proper error handling and logging.
```

### Task 3.2: Create Resolution Analytics

```
Create a file called "tools/analytics.py" that generates reports and analytics about validation failures and resolutions.

Implement these reports:
1. Failure trends over time
2. Most common failure types
3. Provider-specific failure patterns
4. Resolution efficiency metrics
5. CPT code combinations frequently causing issues

Generate reports in both JSON and CSV formats. Include visualization options using matplotlib for key metrics.

Use our existing database service for data access and follow our project's patterns.
```

### Task 3.3: Flask Dashboard (optional)

```
Create a simple Flask web application in a new directory "dashboard/" that provides a web interface for the resolution system.

Include these features:
1. Dashboard with failure statistics
2. Filterable list of failures
3. Detailed failure view with resolution history
4. Status updates and note adding
5. Batch processing interface
6. Analytics visualizations

Use Flask, SQLAlchemy, and a simple Bootstrap template. Keep it lightweight and focused on functionality rather than advanced UI features.

Use our existing resolution database service for data access.
```

---

## General Improvement Prompts

### Improving Error Messages

```
Review our current error messages in core/services/logger.py and suggest improvements to make them more specific and actionable.

For each error type (MOD_001, UNIT_001, RATE_001, BNDL_001, LINE_001), provide:
1. A clearer error message template
2. Specific data points to include in the message
3. 3-5 concrete resolution steps

Follow our existing patterns but focus on making the errors more useful for resolving issues.
```

### Code Refactoring

```
Review the following file: [FILENAME] and suggest refactoring improvements that would:
1. Make the code more maintainable
2. Improve error handling
3. Better separate concerns
4. Follow best practices

Provide specific code changes rather than general suggestions. Maintain compatibility with our existing codebase.
```

### Test Case Creation

```
Create test cases for our validator in: [VALIDATOR_FILENAME]

Write pytest functions that:
1. Test successful validation cases
2. Test common failure scenarios
3. Test edge cases (empty data, malformed data, etc.)

Include appropriate fixtures and mocks. Follow our existing test patterns if available, otherwise follow pytest best practices.
```

---

## Implementation Strategy

For best results when implementing this system with Cursor AI:

1. **Start with understanding**: Before generating any code, ask Cursor AI to explain the existing code structure and flow
2. **Focus on one component at a time**: Complete each task before moving to the next
3. **Request reviews**: After generating code, ask Cursor AI to review it for issues
4. **Iterative refinement**: Make small, focused improvements rather than large rewrites
5. **Test often**: Generate test cases alongside implementation

When facing challenges, try these prompts:

```
I'm getting this error when running the code you generated: [ERROR MESSAGE]
Can you help diagnose the issue and suggest a fix?
```

```
The generated code doesn't match our existing patterns. Specifically, [ISSUE DESCRIPTION].
Can you revise it to be more consistent with our codebase?
```

```
This part of the functionality isn't working as expected: [DESCRIPTION]
Here's the current code: [CODE SNIPPET]
What changes would you recommend?
```

By following this structured approach and using these prompts, you can effectively leverage Cursor AI to implement the bill validation system improvements in manageable phases.