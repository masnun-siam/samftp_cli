# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAM-FTP CLI is a modern command-line tool for browsing and playing media files from SAM-FTP servers. It features a rich terminal interface with async operations, caching, bookmarks, batch operations, and extensive UX improvements (Phase 1 completed).

## Essential Commands

### Development
- **Lint code**: `rye lint`
- **Format code**: `rye fmt`
- **Sync dependencies**: `rye sync`
- **Run from source**: `python -m samftp_cli.main`

### Installation
- **Unix/macOS**: `./install.sh` (makes `samftp` command globally available)
- **Windows**: `install.bat`

### Running
- **Interactive browser**: `samftp`
- **With options**: `samftp --server "Movies" --player mpv`
- **TUI mode**: `samftp --tui` (experimental)
- **Configuration wizard**: `samftp config`
- **Show help**: `samftp --help`

### Subcommands
- **Config management**: `samftp config`, `samftp config-add`, `samftp config-validate`, `samftp config-path`
- **Cache management**: `samftp cache-stats`, `samftp cache-clear`
- **Bookmarks**: `samftp bookmarks-list`

## Configuration

The application requires a configuration file at `~/.samftp-cli.env` (on macOS/Linux) or `%USERPROFILE%\.samftp-cli.env` (on Windows).

### Configuration Format
```env
# Basic server
SERVER_N_NAME="Display Name"
SERVER_N_URL="http://server.url/path/"

# Server with authentication (NEW in Phase 1)
SERVER_N_USERNAME="username"
SERVER_N_PASSWORD="password"
SERVER_N_PREFERRED_PLAYER="mpv"

# Global settings (NEW in Phase 1)
DEFAULT_PLAYER="mpv"
DEFAULT_DOWNLOAD_DIR="/path/to/downloads"
```

### First Run
On first launch, an interactive wizard automatically guides users through configuration setup, including:
- Server details (name, URL)
- Authentication credentials (if needed)
- Connection testing
- Player selection

## Architecture

### Phase 1 Major Changes

The application was significantly refactored in Phase 1 with the following improvements:
- **Async/Await**: Migrated from synchronous to async operations using aiohttp
- **Rich UI**: Replaced basic ANSI colors with Rich library for beautiful terminal output
- **Click Framework**: Migrated from simple argparse to Click for professional CLI
- **Caching System**: Added TTL-based directory caching for performance
- **Bookmarks**: Implemented persistent bookmark system
- **Session Management**: Added AppSession for state tracking
- **Better Error Handling**: Custom exceptions with retry logic and exponential backoff

### Core Application Flow (Updated)

1. **main.py**: CLI entry point with Click framework
   - Handles command-line arguments and flags (--tui, --server, --player, --config)
   - Manages subcommands (config, cache-*, bookmarks-*)
   - Detects first-run and launches setup wizard
   - Loads servers from config
   - Creates aiohttp session for connection pooling
   - Runs async main loop with navigation state tracking
   - Supports both CLI mode and TUI mode
   - **Error logging**: Logs exceptions with full traceback to user log directory

2. **config.py**: Configuration management with interactive wizard
   - Loads server configurations with authentication support
   - Validates URLs and connection credentials
   - Tests server connectivity before saving
   - Interactive wizard for adding servers
   - First-run detection and auto-setup
   - Player preference persistence
   - Download directory management
   - Configuration validation with detailed error reporting

3. **ftp_client.py**: Async HTTP-based FTP operations
   - **Async operations**: Uses aiohttp.ClientSession for non-blocking I/O
   - **Caching**: Integrates with cache manager for directory listings
   - **Custom exceptions**: FTPClientError, ConnectionError, AuthenticationError, NotFoundError, ServerError, TimeoutError
   - **Retry logic**: Automatic retry with exponential backoff (3 attempts)
   - **Authentication**: HTTP Basic Auth support via aiohttp.BasicAuth
   - **Progress tracking**: Rich progress bars with speed and ETA
   - **Download management**: Configurable locations, overwrite handling
   - Parses HTML using BeautifulSoup (looks for `td.fb-n` elements)

4. **ui.py**: Rich terminal user interface
   - **Breadcrumb navigation**: Shows current path with server name
   - **Rich tables**: Formatted directory listings with file type icons
   - **Batch selection**: Multi-select mode with ranges (e.g., "1,3,5-8")
   - **Bookmarks integration**: Add/view/navigate bookmarks
   - **Help system**: In-app command reference
   - **File type icons**: 📁 folders, ▶️ videos, 🎵 audio, 🖼️ images
   - **Color coding**: Different colors for file types
   - **Interactive prompts**: Using Rich's Prompt for better UX
   - Integrates fzf for fuzzy file search

5. **player.py**: Media player integration with persistence
   - **Player preference hierarchy**:
     1. CLI override (--player flag)
     2. Session cache (remembers during session)
     3. Saved preference (from config)
     4. User prompt
   - **Background playback**: Non-blocking with subprocess.Popen
   - **Expanded formats**: Videos, audio (MP3, FLAC, M4A, etc.), images
   - **Player management**: Change player mid-session
   - **Preference persistence**: Save player choice to config
   - Detects available players (mpv, VLC, IINA)
   - Creates temporary M3U playlists for batch playback

6. **data_models.py**: Type definitions and utilities
   - **Server**: name, url, username, password, last_accessed, preferred_player
   - **File**: name, url, size (optional)
   - **Folder**: name, url
   - **Bookmark**: name, server, url, timestamp
   - **CacheEntry**: url, timestamp, folders, files
   - **AppSession**: Runtime state container (selected_server, selected_player, download_directory, history, current_url)
   - **Utilities**: format_file_size(), parse_url_path()

7. **cache.py**: Directory listing cache manager (NEW)
   - **TTL-based caching**: 5-minute default expiration
   - **Memory + disk**: Two-tier caching strategy
   - **Cache operations**: get, set, invalidate, clear, cleanup
   - **Statistics**: Cache size, valid/expired entries, location
   - Uses platformdirs for cross-platform cache location
   - JSON-based persistent storage

8. **bookmarks.py**: Bookmark management system (NEW)
   - **CRUD operations**: Add, remove, update, list bookmarks
   - **Persistence**: JSON storage in user config directory
   - **Server grouping**: Get bookmarks by server
   - **Import/export**: Backup and restore bookmarks
   - **Duplicate detection**: Prevents duplicate bookmark names
   - Uses platformdirs for cross-platform config location

9. **tui.py**: Textual-based TUI (NEW, experimental)
   - **Framework**: Built with Textual for rich terminal UI
   - **Basic skeleton**: Server list, bookmarks sidebar, file browser
   - **Keyboard shortcuts**: q (quit), r (refresh), b (bookmarks), h (help)
   - **Future expansion**: Full mouse support, async loading, context menus
   - Note: CLI mode is fully functional; TUI is a framework for future development

### Key Design Patterns

- **Async/Await**: Non-blocking I/O throughout the application
- **Connection Pooling**: Single aiohttp session shared across requests
- **Session Management**: AppSession tracks state across navigation
- **Rich Formatting**: Consistent use of Rich library for all output
- **Click Commands**: Professional CLI with subcommands and options
- **Caching Strategy**: Two-tier cache (memory + disk) with TTL
- **Preference Hierarchy**: Multiple fallback levels for user preferences
- **Error Recovery**: Retry with exponential backoff, detailed error messages
- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **URL-based Navigation**: Parses HTML directory listings from HTTP servers

### Important Implementation Details

- **HTML Parsing**: Looks for `<td class="fb-n">` elements containing `<a>` tags
- **Parent Directory**: Adds ".." entry by constructing URL with `urljoin(base_url, "..")`
- **File Type Detection**: Extended support for videos, audio, images based on extensions
- **Player Selection**: Four-level hierarchy (override > session > saved > prompt)
- **Playlist Format**: M3U for mpv, multiple URLs for VLC/IINA
- **Background Playback**: Uses subprocess.Popen with DEVNULL for non-blocking
- **Cache Location**: `~/.cache/samftp-cli/` (macOS/Linux) or equivalent on Windows
- **Config Location**: `~/.samftp-cli.env` in user home directory
- **Bookmarks Location**: `~/.config/samftp-cli/bookmarks.json` (macOS/Linux) or equivalent
- **Batch Selection**: Parses ranges (1-5), singles (3), and combinations (1,3,5-8)
- **Authentication**: HTTP Basic Auth via aiohttp.BasicAuth
- **Retry Strategy**: 3 attempts with 2^n exponential backoff (1s, 2s, 4s)
- **Error Logging**: Exceptions logged with timestamp, context, and full traceback
- **Log Location**: Uses platformdirs for cross-platform log paths:
  - macOS: `~/Library/Logs/samftp-cli/error.log`
  - Linux: `~/.local/state/samftp-cli/error.log`
  - Windows: `%LOCALAPPDATA%\samftp-cli\Logs\error.log`

### Navigation Flow

```
Start
  ↓
First Run Check → Yes → Interactive Wizard → Save Config
  ↓ No
Load Servers from Config
  ↓
Validate Config
  ↓
Select Server (or use --server flag)
  ↓
Create aiohttp Session
  ↓
Main Loop:
  ├→ Fetch Directory (check cache first)
  ├→ Parse HTML
  ├→ Display with Rich UI (breadcrumbs + table)
  ├→ Get User Action
  ├→ Handle Action:
  │   ├─ Select file → Play with preferred player (background)
  │   ├─ Select folder → Navigate (add to history)
  │   ├─ Download → Prompt location → Download with progress
  │   ├─ Batch select → Multi-select → Download or Play
  │   ├─ Search → FZF → Select
  │   ├─ Bookmark → Add/View/Navigate
  │   ├─ Refresh → Invalidate cache → Reload
  │   └─ Quit → Exit
  └→ Loop
```

## Development Practices

This project emphasizes:
- **Type hints** for all functions (strictly enforced)
- **Descriptive naming** for variables and functions
- **Modular design** with clear separation of concerns
- **Async/await** for all I/O operations
- **Rich formatting** for all terminal output (no raw print statements)
- **Environment-based configuration** (no hardcoded values)
- **Robust error handling** with custom exceptions and retry logic
- **Dependency management** via Rye
- **Code style** enforced with Ruff
- **Click framework** for CLI commands (not argparse)
- **Session management** for state tracking

## External Dependencies

### Required System Tools
- **mpv, VLC, or IINA**: At least one media player must be installed
- **fzf**: Optional but recommended for search functionality

### Python Dependencies (Updated in Phase 1)
- **requests**: Legacy HTTP support (being phased out)
- **aiohttp**: Async HTTP client (primary)
- **beautifulsoup4**: HTML parsing for directory listings
- **python-dotenv**: Configuration file loading
- **pyfzf**: Python wrapper for fzf integration
- **rich**: Terminal formatting and styling (NEW)
- **textual**: TUI framework (NEW, optional)
- **click**: CLI framework (NEW)
- **aiofiles**: Async file I/O (NEW)
- **platformdirs**: Cross-platform directory paths (NEW)

## Common Development Tasks

### Adding a new CLI command
1. Add command function in main.py with `@cli.command()` decorator
2. Use Rich console for output
3. Handle errors gracefully
4. Update --help documentation

### Adding a new feature to UI
1. Update ui.py with new command key
2. Add to display_help() table
3. Handle in browse_directory() action switch
4. Use Rich formatting for output
5. Test with different file types

### Modifying cache behavior
1. Adjust TTL in cache.py or pass to CacheManager()
2. Update cache_file location if needed
3. Test cache hit/miss scenarios
4. Ensure proper invalidation on refresh

### Adding authentication for new server type
1. Extend Server dataclass in data_models.py if needed
2. Update config.py to parse new fields
3. Modify ftp_client.py to handle new auth type
4. Test connection with test_server_connection()

### Debugging tips
- Check cache stats: `samftp cache-stats`
- Clear cache: `samftp cache-clear`
- Validate config: `samftp config-validate`
- Run with verbose Python: `python -v -m samftp_cli.main`
- Check log output (Rich prints to stderr by default)
- **Check error logs**: When exceptions occur, full traceback is logged to:
  - macOS: `~/Library/Logs/samftp-cli/error.log`
  - Linux: `~/.local/state/samftp-cli/error.log`
  - Windows: `%LOCALAPPDATA%\samftp-cli\Logs\error.log`
- **View recent errors**: `tail -f ~/Library/Logs/samftp-cli/error.log` (macOS)

## Testing Checklist

When making changes, test:
- [ ] First-run experience (delete ~/.samftp-cli.env and rerun)
- [ ] Server selection with multiple servers
- [ ] Authentication (if applicable)
- [ ] Directory navigation (folders, parent directory)
- [ ] File playback (video, audio, image)
- [ ] Download (single file, all files, batch)
- [ ] Batch selection mode
- [ ] Bookmarks (add, list, navigate)
- [ ] Cache (stats, clear, hit/miss)
- [ ] Player preference persistence
- [ ] Background playback (media plays while browsing)
- [ ] Error scenarios (network error, auth failure, 404)
- [ ] CLI flags (--server, --player, --tui)
- [ ] All subcommands (config, cache-*, bookmarks-*)

## Future Expansion (Phase 2+)

Areas for potential development:
- Complete TUI implementation with mouse support
- File filtering and sorting
- Deep search across entire server
- Download queue with pause/resume
- Parallel downloads with configurable threads
- Subtitle auto-detection and loading
- Playlist management (save, edit, export)
- Command history with navigation
- File information view (size, date, metadata)
- Server statistics and content overview
