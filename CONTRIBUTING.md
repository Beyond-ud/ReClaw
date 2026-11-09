# Contributing to ReClaw

Thank you for your interest in contributing to ReClaw! 🦞

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists in [Issues](https://github.com/Beyond-ud/ReClaw/issues)
2. Open a new issue with:
   - Device model and Android version
   - Steps to reproduce
   - Expected vs actual behavior
   - Termux and Termux:API versions

### Suggesting Features

Open an issue with the tag `enhancement` and describe:
- What problem does it solve?
- How should it work?
- Which skill does it relate to? (routine-manager, commute-planner, notification-hub, smart-customizer)

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test on a real Android device (or Termux emulator)
5. Submit a Pull Request with a clear description

### Code Style

- Python: Follow PEP 8
- Go: Run `gofmt` before committing
- Keep functions small and well-documented
- Add comments for non-obvious logic

### Adding a New Skill

1. Create a new directory under `skills/your-skill-name/`
2. Add a `SKILL.md` with behavior rules and available tools
3. Register the skill in `demo/reclaw_agent.py`
4. Add training examples to `model/dataset/`

## Development Setup

```bash
# Clone
git clone https://github.com/Beyond-ud/ReClaw.git
cd ReClaw

# Install dependencies (Termux)
pkg install python llama.cpp termux-api

# Run agent
python3 demo/reclaw_agent.py
```

## Questions?

Open an issue or reach out to the team. We're happy to help!
