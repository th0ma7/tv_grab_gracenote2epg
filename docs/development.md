# Development Guide

This guide covers development setup, testing, validation, and contribution guidelines for gracenote2epg.

## Development Environment Setup

### Prerequisites

```bash
# Python 3.7+ required
python3 --version

# Git for version control
git --version

# Recommended: Virtual environment
python3 -m venv gracenote_dev
source gracenote_dev/bin/activate  # Linux/Mac
# gracenote_dev\Scripts\activate   # Windows
```

### Installation for Development

```bash
# Clone repository
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg

# Install in editable mode with all features
pip install -e .[dev]

# Or install dependencies manually
pip install -e .
pip install langdetect polib pytest flake8 black mypy
```

### Development Dependencies

```python
# setup.py extras_require['dev']
'dev': [
    'langdetect>=1.0.9',      # Language detection
    'polib>=1.1.0',           # Translations
    'pytest>=6.0',            # Testing framework
    'flake8>=3.8',            # Code linting
    'black>=21.0',            # Code formatting
    'mypy>=0.910',            # Type checking
],
```

## Project Structure

```
gracenote2epg/
├── gracenote2epg/           # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point for -m execution
│   ├── core.py              # Core grabber logic
│   ├── config.py            # Configuration handling
│   ├── cache.py             # Cache management
│   └── utils.py             # Utility functions
├── tv_grab_gracenote2epg    # XMLTV wrapper script
├── gracenote2epg.xml        # Default configuration template
├── docs/                    # Documentation
├── tests/                   # Test suite (if present)
├── setup.py                 # Package setup
├── MANIFEST.in              # Distribution file manifest
└── README.md                # Main documentation
```

## Code Quality and Standards

### Code Formatting

```bash
# Format code with Black
black gracenote2epg/ tv_grab_gracenote2epg

# Check formatting
black --check gracenote2epg/
```

### Linting

```bash
# Lint with flake8
flake8 gracenote2epg/ tv_grab_gracenote2epg

# Configuration in setup.cfg or .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = build,dist,*.egg-info
```

### Type Checking

```bash
# Type check with mypy
mypy gracenote2epg/

# Configuration in setup.cfg
[mypy]
python_version = 3.7
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

## Testing and Validation

### Unit Tests

```bash
# Run tests with pytest
pytest tests/

# Run with coverage
pytest --cov=gracenote2epg tests/

# Run specific test
pytest tests/test_config.py::test_configuration_parsing
```

### Integration Testing

```bash
# Test basic functionality
./tv_grab_gracenote2epg --capabilities

# Test lineup detection (requires internet)
./tv_grab_gracenote2epg --show-lineup --zip 92101

# Test full download (small dataset)
./tv_grab_gracenote2epg --days 1 --zip 92101 --debug --console
```

### XMLTV Validation

#### Technical XMLTV Validation (Development)

```bash
# Download XMLTV DTD for validation
wget http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd

# Validate XMLTV output against DTD
xmllint --noout --dtdvalid xmltv.dtd ~/gracenote2epg/cache/xmltv.xml

# Check for well-formed XML
xmllint --noout ~/gracenote2epg/cache/xmltv.xml && echo "Well-formed XML"

# Validate encoding
file ~/gracenote2epg/cache/xmltv.xml  # Should show UTF-8
```

#### XMLTV Content Validation

```bash
# Check program count
grep -c "programme start=" ~/gracenote2epg/cache/xmltv.xml

# Check channel count  
grep -c "channel id=" ~/gracenote2epg/cache/xmltv.xml

# Validate time formats (should be XMLTV format: YYYYMMDDHHMMSS +TZTZ)
grep "programme start=" ~/gracenote2epg/cache/xmltv.xml | head -5

# Check for required elements
grep -c "<title" ~/gracenote2epg/cache/xmltv.xml     # Program titles
grep -c "<desc" ~/gracenote2epg/cache/xmltv.xml      # Descriptions
grep -c "<category" ~/gracenote2epg/cache/xmltv.xml  # Categories
```

#### XMLTV Standards Compliance

```bash
# Check DOCTYPE declaration
head -5 ~/gracenote2epg/cache/xmltv.xml | grep DOCTYPE

# Expected: <!DOCTYPE tv SYSTEM "xmltv.dtd">

# Check generator information
grep "generator-info" ~/gracenote2epg/cache/xmltv.xml

# Check encoding declaration
head -1 ~/gracenote2epg/cache/xmltv.xml | grep "encoding"
```

### Performance Testing

```bash
# Test cache efficiency
./tv_grab_gracenote2epg --days 7 --zip 92101 --debug | grep -i "cache"

# Measure execution time
time ./tv_grab_gracenote2epg --days 1 --zip 92101

# Test memory usage
/usr/bin/time -v ./tv_grab_gracenote2epg --days 1 --zip 92101
```

## Building and Distribution

### Building Source Distribution

```bash
# Install build tools
pip install build twine

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build source distribution and wheel
python -m build

# Check distribution contents
tar -tzf dist/gracenote2epg-*.tar.gz | head -20
```

### Testing Distribution

```bash
# Test source distribution installation
pip install dist/gracenote2epg-*.tar.gz[full]

# Test wheel installation  
pip install dist/gracenote2epg-*-py3-none-any.whl[full]

# Verify commands work
tv_grab_gracenote2epg --capabilities
gracenote2epg --version
```

### Publishing to PyPI

```bash
# Test upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ gracenote2epg[full]

# Upload to production PyPI
python -m twine upload dist/*
```

## Debugging and Troubleshooting

### Debug Mode

```bash
# Enable all debug output
./tv_grab_gracenote2epg --debug --console --days 1 --zip 92101

# Specific debug areas (modify source as needed)
# - Configuration parsing
# - Lineup detection  
# - Download progress
# - Cache operations
# - XMLTV generation
```

### Log Analysis

```bash
# Real-time log monitoring
tail -f ~/gracenote2epg/log/gracenote2epg.log

# Search for specific issues
grep -i error ~/gracenote2epg/log/gracenote2epg.log
grep -i warning ~/gracenote2epg/log/gracenote2epg.log

# Performance analysis
grep "took.*seconds" ~/gracenote2epg/log/gracenote2epg.log
grep "cache efficiency" ~/gracenote2epg/log/gracenote2epg.log
```

### Common Development Issues

#### Import Errors
```bash
# Check package installation
pip show gracenote2epg

# Verify Python path
python -c "import sys; print(sys.path)"

# Test module import
python -c "import gracenote2epg; print('OK')"
```

#### Configuration Issues
```bash
# Test configuration parsing
python -c "
from gracenote2epg.config import Config
config = Config()
print('Configuration loaded successfully')
"
```

## Contributing Guidelines

### Code Style

- **Follow PEP 8** with Black formatting
- **Line length**: 88 characters (Black default)
- **Type hints**: Required for new code
- **Docstrings**: Use Google style docstrings

### Commit Guidelines

```bash
# Commit message format
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance
```

### Pull Request Process

1. **Fork repository** and create feature branch
2. **Make changes** with appropriate tests
3. **Run quality checks**: `black`, `flake8`, `mypy`, `pytest`
4. **Update documentation** if needed
5. **Submit pull request** with clear description

### Testing Requirements

- **Unit tests** for new functionality
- **Integration tests** for major features
- **XMLTV validation** for output changes
- **Performance testing** for cache/network changes

## Architecture Notes

### Core Components

- **Configuration**: XML-based with auto-migration
- **Cache System**: Intelligent block-based caching
- **Download Engine**: WAF-aware with retry logic
- **XMLTV Generator**: Standards-compliant output
- **TVheadend Integration**: Optional channel filtering

### Design Principles

- **Backward compatibility** with zap2epg configurations
- **Graceful degradation** when optional features unavailable
- **Intelligent caching** for 95%+ cache efficiency
- **Robust error handling** with automatic retries
- **Platform agnostic** auto-detection

## Release Process

### Version Management

```bash
# Update version in setup.py
version='1.5'

# Tag release
git tag -a v1.5 -m "Release version 1.5"
git push origin v1.5
```

### Release Checklist

1. **Update CHANGELOG.md** with new features/fixes
2. **Run full test suite** including integration tests
3. **Update version number** in setup.py
4. **Build distributions** and test installation
5. **Update documentation** if needed
6. **Create Git tag** and push
7. **Upload to PyPI** after final testing
8. **Update installation instructions** in documentation

## Getting Help

### Development Support

- **[GitHub Issues](https://github.com/th0ma7/gracenote2epg/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/th0ma7/gracenote2epg/discussions)** - Development questions
- **Code Review** - Submit pull requests for feedback

### Resources

- **[XMLTV DTD](http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd)** - XMLTV standard
- **[Python Packaging](https://packaging.python.org/)** - Distribution guidelines
- **[TVheadend API](https://tvheadend.org/projects/tvheadend/wiki/Httpapi)** - Integration reference
