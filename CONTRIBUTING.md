# Contributing

Thanks for contributing to the Authorized Lab IDS Dashboard.

## Scope and Safety

- This repository is strictly defensive, educational, and intended for authorized lab use.
- Do not propose or contribute offensive functionality, exploit delivery, credential theft, stealth, persistence, bypasses, unauthorized scanning, or real-world abuse workflows.
- If a feature is dual-use, keep the implementation limited to safe local-lab or sample-data behavior.

## Development Workflow

1. Create a virtual environment and install dependencies:

   ```bash
   make setup
   ```

2. Run the test suite before opening a pull request:

   ```bash
   make test
   ```

3. Keep the project runnable at each step. If you change docs or commands, verify they still match the actual code.

## Contribution Expectations

- Prefer small, reviewable pull requests.
- Add or update tests for behavior changes.
- Keep modules clean, documented, and beginner-friendly.
- Preserve secure defaults and centralized validation/error handling patterns.
- Update the README when the public workflow, architecture, or environment variables change.

## Pull Request Checklist

- Tests pass locally.
- README and docs are updated if behavior changed.
- New sample data is safe, synthetic, and authorized-lab appropriate.
- No secrets, private logs, or sensitive network data are included.

