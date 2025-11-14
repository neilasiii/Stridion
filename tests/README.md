# Test Suite

This directory contains the test suite for the running-coach health data sync system.

## Setup

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Run specific test file
```bash
pytest tests/test_sync_health_data.py
pytest tests/test_health_data_parser.py
```

### Run specific test class
```bash
pytest tests/test_sync_health_data.py::TestPathValidation
```

### Run specific test method
```bash
pytest tests/test_sync_health_data.py::TestPathValidation::test_path_traversal_attacks
```

### Run with verbose output
```bash
pytest -v
```

## Test Status

**Current Status (4 passing, 33 skipped):**
- ✓ Error handling tests pass without dependencies
- ⏭️ Security tests require Google Drive dependencies (skip if not installed)
- ⏭️ Parser tests require full directory structure (TODO: refactor)

To run security tests, install Google Drive dependencies:
```bash
pip install -r requirements.txt
```

## Test Coverage

Current test coverage includes:

### Google Drive Sync (`test_sync_health_data.py`)
- **Path Validation**: Directory traversal attacks, absolute paths, dangerous characters, path length limits
- **Config Validation**: Missing config, invalid JSON, missing fields, invalid folder IDs, empty values
- **File Size Validation**: Type checking, positive values, upper limits, integer/float support
- **Sync State Management**: Loading/saving state, handling corrupted state files
- **Error Handling**: Custom exception types and messages

### Health Data Parser (`test_health_data_parser.py`)
- **Activity Parsing**: Running/walking activities, missing heart rate data, multiple activities, malformed rows
- **Sleep Parsing**: Complete sessions, sleep efficiency calculations
- **VO2 Max Parsing**: Reading validation
- **Weight Parsing**: Body composition data, missing composition fields
- **Resting HR Parsing**: Single and multiple readings

## Test Structure

```
tests/
├── __init__.py                      # Package initialization
├── README.md                        # This file
├── test_sync_health_data.py         # Google Drive sync tests
└── test_health_data_parser.py       # Health data parser tests
```

## Writing New Tests

Follow these guidelines when adding tests:

1. **Use descriptive test names**: `test_path_traversal_attacks` not `test_security`
2. **Use subTest for parametric tests**: Test multiple inputs with clear labels
3. **Clean up resources**: Use `setUp()` and `tearDown()` for temporary files
4. **Test both success and failure cases**: Happy path AND error conditions
5. **Keep tests isolated**: Each test should be independent
6. **Use appropriate assertions**: `assertEqual`, `assertRaises`, `assertIsNone`, etc.

## Security Testing

The test suite includes comprehensive security validation:

- **Path Traversal**: `../`, absolute paths, null bytes, shell injection attempts
- **Input Validation**: Type checking, range validation, length limits
- **Configuration Security**: Required fields, format validation, safe defaults
- **Error Handling**: Proper exception types, informative messages

## Continuous Integration

To integrate with CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    pytest --cov=src --cov-report=xml
```

## Troubleshooting

**Import errors**: Ensure you're running pytest from the project root directory

**Missing modules**: Install development dependencies with `pip install -r requirements-dev.txt`

**Permission errors**: Check that temporary directories are writable

**Stale .pyc files**: Clear with `find . -type f -name "*.pyc" -delete`
