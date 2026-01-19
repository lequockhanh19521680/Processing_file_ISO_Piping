# Contributing to ISO Piping File Processor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/Processing_file_ISO_Piping.git
   cd Processing_file_ISO_Piping
   ```
3. **Set up the development environment** following the README.md instructions

## Development Workflow

### 1. Create a Branch

Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### 2. Make Changes

- Follow the existing code style and patterns
- Write clean, readable, and well-commented code
- Keep commits focused and atomic
- Test your changes thoroughly

### 3. Test Your Changes

#### Backend Testing:
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Test imports and basic functionality
python -c "import main; import drive_service; import pdf_utils; import excel_utils; print('All imports successful')"

# Run the server and test endpoints
python main.py
```

#### Frontend Testing:
```bash
cd frontend

# Install dependencies
npm install

# Build and check for errors
npm run build

# Run development server
npm run dev
```

### 4. Commit Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: description of what was added"
```

Good commit messages:
- Start with a verb (Add, Fix, Update, Remove, Refactor)
- Be concise but descriptive
- Explain why, not just what

Examples:
- ✅ "Add OCR support for scanned PDFs"
- ✅ "Fix folder ID extraction for alternate URL formats"
- ✅ "Update README with Docker deployment instructions"
- ❌ "Changes"
- ❌ "Fixed stuff"

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what was changed and why
- Reference to any related issues
- Screenshots for UI changes
- Test results if applicable

## Code Style Guidelines

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable names

Example:
```python
def extract_folder_id(self, drive_link: str) -> str:
    """
    Extract folder ID from Google Drive URL.
    
    Args:
        drive_link: Google Drive folder URL
        
    Returns:
        Extracted folder ID
    """
    # Implementation...
```

### JavaScript/React (Frontend)

- Use functional components with hooks
- Follow existing component structure
- Use meaningful variable and function names
- Add comments for complex logic
- Keep components focused and reusable

Example:
```javascript
const handleSubmit = async (event) => {
  event.preventDefault();
  
  // Validation
  if (!file) {
    setError('Please select a file');
    return;
  }
  
  // Process...
};
```

### CSS

- Use existing naming conventions
- Keep selectors simple and specific
- Group related properties together
- Comment complex styling decisions

## Project Structure

Understanding the project structure:

```
Processing_file_ISO_Piping/
├── backend/              # Python FastAPI backend
│   ├── main.py          # API endpoints and orchestration
│   ├── drive_service.py # Google Drive integration
│   ├── pdf_utils.py     # PDF text extraction
│   ├── excel_utils.py   # Excel file processing
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend
│   ├── src/
│   │   ├── App.jsx     # Main component
│   │   └── ...
│   └── package.json    # Node dependencies
├── ai-context/          # AI-friendly documentation
├── examples/            # Sample files and utilities
└── README.md           # Main documentation
```

## Adding New Features

When adding new features:

1. **Review AI Context Files**: Check `ai-context/` for architecture and design patterns
2. **Follow Existing Patterns**: Maintain consistency with existing code
3. **Update Documentation**: Update README.md and relevant AI context files
4. **Add Examples**: Include usage examples if applicable
5. **Consider Performance**: Think about scalability and resource usage
6. **Handle Errors**: Add proper error handling and user-friendly messages

## Common Contribution Areas

### Backend Enhancements

- **PDF Processing**: OCR support, better text extraction
- **Performance**: Async operations, caching strategies, parallel processing
- **Google Drive**: Additional file types, multiple folders, advanced filters
- **API**: New endpoints, batch processing, webhooks
- **Database**: Persistent caching, job queuing, result history

### Frontend Improvements

- **UI/UX**: Better progress indicators, drag-and-drop upload, result preview
- **Validation**: Client-side validation, file type checking
- **Features**: Multiple file upload, history view, settings panel
- **Mobile**: Responsive design improvements
- **Accessibility**: ARIA labels, keyboard navigation

### Documentation

- **Tutorials**: Step-by-step guides for common tasks
- **API Documentation**: Detailed endpoint documentation
- **Deployment**: AWS, Azure, Docker guides
- **Troubleshooting**: Common issues and solutions
- **AI Context**: Keep AI context files updated

## Testing Guidelines

### Manual Testing Checklist

Before submitting a PR, test:

- [ ] Backend starts without errors
- [ ] Frontend builds successfully
- [ ] Can upload valid Excel file
- [ ] Can enter Google Drive link
- [ ] Processing completes without errors
- [ ] Result file downloads correctly
- [ ] Error handling works for invalid inputs
- [ ] UI is responsive and user-friendly

### Automated Testing (Future)

If adding tests:
- Place backend tests in `backend/tests/`
- Place frontend tests in `frontend/src/__tests__/`
- Ensure all tests pass before submitting PR
- Add tests for new features

## Reporting Issues

When reporting bugs:

1. **Check existing issues** first
2. **Use the issue template** if available
3. **Include**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Environment details (OS, Python version, Node version)
   - Screenshots if applicable

## Feature Requests

When requesting features:

1. **Check existing issues** to avoid duplicates
2. **Describe the problem** the feature would solve
3. **Explain the proposed solution**
4. **Consider alternatives** and trade-offs
5. **Provide use cases** and examples

## Code Review Process

Pull requests will be reviewed for:

- **Functionality**: Does it work as intended?
- **Code Quality**: Is it clean, readable, and maintainable?
- **Tests**: Are there adequate tests?
- **Documentation**: Is documentation updated?
- **Performance**: Any performance implications?
- **Security**: Any security concerns?
- **Breaking Changes**: Does it maintain backward compatibility?

## Security

- **Never commit credentials** (service account files, API keys)
- **Review .gitignore** before committing
- **Sanitize inputs** to prevent injection attacks
- **Handle errors** without exposing sensitive information
- **Report security issues** privately (don't open public issues)

## Questions?

- **Documentation**: Check README.md and ai-context/ files
- **Issues**: Open a GitHub issue for questions
- **Discussions**: Use GitHub Discussions for general questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to ISO Piping File Processor! 🎉
