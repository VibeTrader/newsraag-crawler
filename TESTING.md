test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        python run_tests.py unit -v -c
    
    - name: Run integration tests
      run: |
        python run_tests.py integration -v
      env:
        # Test environment variables
        QDRANT_URL: http://localhost:6333
        OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_API_KEY }}
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

## 🛠️ Troubleshooting

### Common Issues

1. **Import Errors**
```bash
# Fix Python path issues
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# Or on Windows
set PYTHONPATH=%PYTHONPATH%;%CD%
```

2. **Missing Test Dependencies**
```bash
# Reinstall test requirements
pip install -r requirements-test.txt --force-reinstall
```

3. **Async Test Issues**
```python
# Ensure proper async test setup
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

4. **Mock Issues**
```python
# Use AsyncMock for async functions
from unittest.mock import AsyncMock

@patch('module.async_function', new_callable=AsyncMock)
async def test_with_async_mock(mock_func):
    mock_func.return_value = "test"
    result = await my_function()
    assert result == "test"
```

### Performance Issues

1. **Slow Tests**
```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Profile slow tests
pytest tests/ --durations=10
```

2. **Memory Issues**
```bash
# Run tests with memory monitoring
pytest tests/ --memray

# Or use built-in memory profiler
python -m pytest tests/ -s --tb=short
```

### External Service Issues

1. **Qdrant Connection Failures**
```python
# Use test fixtures with proper mocking
@pytest.fixture
def mock_qdrant_client():
    with patch('clients.qdrant_client.QdrantClientWrapper') as mock:
        yield mock.return_value
```

2. **Azure Service Timeouts**
```bash
# Run without external dependencies
pytest tests/ -m "not external"
```

## 📈 Test Metrics and Reporting

### Test Metrics to Track
- **Test Coverage**: Percentage of code covered by tests
- **Test Duration**: How long tests take to run
- **Flaky Tests**: Tests that intermittently fail
- **Test Success Rate**: Percentage of successful test runs

### Automated Reporting
```bash
# Generate JSON report for CI/CD
pytest tests/ --json-report --json-report-file=test-report.json

# Generate JUnit XML for CI/CD systems
pytest tests/ --junitxml=junit.xml

# Generate HTML report
pytest tests/ --html=test-report.html --self-contained-html
```

## 🎯 Testing Checklist

### Before Committing Code
- [ ] All unit tests pass locally
- [ ] New code has corresponding tests
- [ ] Coverage remains above 70%
- [ ] No linting errors
- [ ] Integration tests pass (if applicable)

### Before Releasing
- [ ] All tests pass in CI/CD pipeline
- [ ] Performance tests show no regression
- [ ] Integration tests pass with real services
- [ ] Documentation updated
- [ ] Test coverage report generated

## 📚 Advanced Testing Patterns

### Testing Async Code
```python
@pytest.mark.asyncio
async def test_async_crawl_source():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")
        assert result is not None
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
def test_url_normalization(url_input):
    result = normalize_url(url_input)
    assert isinstance(result, str)
```

### Parameterized Tests
```python
@pytest.mark.parametrize("input_url,expected", [
    ("https://example.com", "https://example.com"),
    ("http://example.com", "https://example.com"),
    ("example.com", "https://example.com"),
])
def test_url_normalization_cases(input_url, expected):
    assert normalize_url(input_url) == expected
```

### Database Testing with Fixtures
```python
@pytest.fixture
def clean_database():
    # Setup clean database state
    yield
    # Cleanup after test
    cleanup_test_data()
```

### Testing Error Conditions
```python
def test_handles_network_timeout():
    with patch('requests.get') as mock_get:
        mock_get.side_effect = requests.Timeout()
        
        result = fetch_article("https://example.com")
        
        assert result is None
        # Verify proper error handling
```

## 🔍 Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with Python debugger
python -m pytest tests/unit/test_metrics.py::test_start_cycle -s --pdb

# Run with verbose output
python run_tests.py unit -v

# Run specific failing test
python run_tests.py test tests/unit/test_monitoring/test_metrics.py::TestMetrics::test_start_cycle -v
```

### Using Test Logs
```python
import logging

def test_with_logging(caplog):
    with caplog.at_level(logging.INFO):
        my_function_that_logs()
    
    assert "Expected log message" in caplog.text
```

### Debugging Async Issues
```python
import asyncio

@pytest.mark.asyncio
async def test_debug_async():
    # Set event loop debug mode
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    
    result = await my_async_function()
    assert result is not None
```

## 🎉 Success Metrics

Your testing implementation is successful when:

- ✅ **95%+ test reliability**: Tests consistently pass
- ✅ **<30 second feedback loop**: Unit tests run quickly
- ✅ **70%+ code coverage**: Adequate test coverage
- ✅ **Zero flaky tests**: All tests are deterministic
- ✅ **Comprehensive error testing**: Edge cases covered
- ✅ **Easy to run**: Simple commands for all scenarios
- ✅ **Clear test failures**: Descriptive error messages
- ✅ **Automated in CI/CD**: Tests run on every commit

---

## 🚀 Next Steps

1. **Start Testing Implementation**
   ```bash
   # Install dependencies
   python run_tests.py install
   
   # Run existing tests to verify setup
   python run_tests.py unit
   ```

2. **Begin with Core Components**
   - Start with `test_source_crawler.py`
   - Add `test_metrics.py` 
   - Create `test_duplicate_detector.py`

3. **Expand Test Coverage**
   - Add integration tests
   - Implement performance tests
   - Create external service tests

4. **Setup CI/CD Pipeline**
   - Configure GitHub Actions
   - Add coverage reporting
   - Set up automated deployments

Happy testing! 🎯
