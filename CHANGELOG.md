# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-17

### Added
- **Dual-Domain Support**: Seamlessly supports both `notebook.google.com` (post-Gemini rebrand) and legacy `notebooklm.google.com` with centralized URL validation (`is_notebook_url`)
- **Library Update Command**: Added `notebook_manager.py update` CLI subcommand to update notebook metadata without losing creation history
- **Browser Fallback Support**: Added graceful fallback to default Chromium if Google Chrome is not installed on the host
- **Tool-Agnostic Support**: Generalized skill documentation and reminders to support Antigravity, Claude Code, Cursor, and any LLM agent

### Changed
- **Bumped Dependencies**: Updated `patchright` to `1.62.3`
- **Modernized Automation**: Replaced deprecated Playwright typing APIs with resilient sequential typing and `page.fill` fallbacks
- **Session Expiry Thresholds**: Added a 14-day hard expiry check to `auth_manager.py` to prevent hanging on silently expired session cookies

### Fixed
- **Stale Response Detection**: Implemented hash-based pre-submission baselining to prevent stale history from being returned instead of fresh answers
- **Input Field Targeting**: Ensured typing targets the actual chat query textarea rather than header title or search input fields (Issue #54)
- **Use Count Analytics**: Now automatically increments `use_count` and updates `last_used` in `NotebookLibrary` upon successful queries (Issue #55)
- **Windows Setup & Encoding**: Fixed `pip.exe` replacement error during pip upgrades and forced UTF-8 console output for Windows systems
- **Browser Mismatch in Setup**: Aligned browser installation across `setup_environment.py` and `__init__.py`
- **Import Side Effects**: Eliminated blocking venv/browser setup side effects when importing the `scripts` package

## [1.3.0] - 2025-11-21

### Added
- **Modular Architecture** - Refactored codebase for better maintainability
  - New `config.py` - Centralized configuration (paths, selectors, timeouts)
  - New `browser_utils.py` - BrowserFactory and StealthUtils classes
  - Cleaner separation of concerns across all scripts

### Changed
- **Timeout increased to 120 seconds** - Long queries no longer timeout prematurely
  - `ask_question.py`: 30s → 120s
  - `browser_session.py`: 30s → 120s
  - Resolves Issue #4

### Fixed
- **Thinking Message Detection** - Fixed incomplete answers showing placeholder text
  - Now waits for `div.thinking-message` element to disappear before reading answer
  - Answers like "Reviewing the content..." or "Looking for answers..." no longer returned prematurely
  - Works reliably across all languages and NotebookLM UI changes

- **Correct CSS Selectors** - Updated to match current NotebookLM UI
  - Changed from `.response-content, .message-content` to `.to-user-container .message-text-content`
  - Consistent selectors across all scripts

- **Stability Detection** - Improved answer completeness check
  - Now requires 3 consecutive stable polls instead of 1 second wait
  - Prevents truncated responses during streaming

## [1.2.0] - 2025-10-28

### Added
- Initial public release
- NotebookLM integration via browser automation
- Session-based conversations with Gemini 2.5
- Notebook library management
- Knowledge base preparation tools
- Google authentication with persistent sessions
