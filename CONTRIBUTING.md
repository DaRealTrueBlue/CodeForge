# Contributing to CodeForge

Thank you for considering contributing to CodeForge! We welcome all contributions, from bug reports to new features.

## 🐛 Reporting Bugs

If you find a bug, please open an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs actual behaviour
- Your operating system and Python version
- Any relevant error messages or screenshots

## 💡 Suggesting Features

We love new ideas! To suggest a feature:
- Check existing issues to avoid duplicates
- Describe the feature and why it would be useful
- Include mockups or examples if applicable

## 🎨 Contributing Themes

CodeForge supports custom themes! To contribute a theme:

1. Add your theme to the `self.themes` dictionary in `code_editor.py`:
```python
"Your Theme Name": {
    "bg": "#background_colour",
    "fg": "#text_colour",
    "accent": "#accent_colour",
    "border": "#border_colour"
}
```

2. Test the theme thoroughly in the editor
3. Include a screenshot in your pull request
4. Ensure proper contrast for readability

## 🔧 Contributing Code

### Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/darealtrueblue/CodeForge.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Commit with clear messages: `git commit -m "Add: description of your changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a pull request

### Code Style

- Use Australian English for all text (colour, customisation, etc.)
- Follow PEP 8 style guidelines
- Add docstrings to new functions/classes
- Keep functions focused and modular
- Comment complex logic

### Testing

Before submitting:
- Test your changes with multiple file types
- Check that existing features still work
- Test on Windows (primary platform)
- Verify no performance regressions

## 📦 Building from Source

```bash
# Install dependencies
pip install tkinter

# Run directly
python code_editor.py

# Build executable (requires PyInstaller)
pip install pyinstaller
pyinstaller build.spec
```

## 🎯 Areas We Need Help With

- **Themes**: More built-in themes (Solarized, Nord, One Dark, etc.)
- **Syntax Highlighting**: Additional language support
- **Performance**: Optimisations for large files
- **Documentation**: Tutorials, guides, examples
- **Testing**: Bug hunting and edge cases
- **Plugins**: Extension system architecture
- **Cross-platform**: Linux/macOS support

## 📋 Pull Request Guidelines

- Reference any related issues
- Describe what your PR does and why
- Include screenshots for UI changes
- Keep PRs focused on a single feature/fix
- Update documentation if needed
- Ensure all tests pass

## ❓ Questions?

Feel free to open an issue with the "question" label or reach out through the discussions page.

## 📜 Code of Conduct

Please be respectful and constructive in all interactions. See [Code of Conduct](CODE_OF_CONDUCT.md) for details.

---

Thank you for helping make CodeForge better! 🚀
