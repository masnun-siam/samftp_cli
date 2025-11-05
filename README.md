# SAM-FTP CLI

A modern command-line interface to browse and play media from SAM-FTP servers with rich terminal UI, caching, bookmarks, and async operations.

## ✨ Features

### Core Features
- **Beautiful Terminal UI**: Rich formatted output with colors, icons, and tables
- **Async Operations**: Non-blocking downloads and directory browsing with aiohttp
- **Smart Caching**: Directory listings cached with TTL for faster navigation
- **Bookmarks**: Save and quickly access favorite directories
- **Batch Operations**: Multi-select files for download or playlist creation
- **Player Persistence**: Remember your preferred media player
- **Background Playback**: Continue browsing while media plays
- **Authentication**: Support for password-protected servers
- **Interactive Setup**: First-run wizard guides you through configuration

### Media Support
- **Video**: MP4, AVI, MOV, MKV, WebM, FLV, M4V
- **Audio**: MP3, FLAC, M4A, WAV, OGG, AAC
- **Images**: JPG, PNG, GIF, BMP, SVG, WebP
- **Players**: mpv, VLC, IINA (auto-detect and remember preference)

### Advanced Features
- Breadcrumb navigation with path display
- Fuzzy search with `fzf` integration
- Download progress bars with speed and ETA
- Automatic retry with exponential backoff
- Configurable download locations
- CLI subcommands for management
- Optional TUI mode (experimental)

## Prerequisites

- **Python 3.8+**
- **Media Player**: At least one of:
  - [mpv](https://mpv.io/installation/) (recommended)
  - [VLC](https://www.videolan.org/vlc/)
  - [IINA](https://iina.io/) (macOS only)
- **Optional**: [fzf](https://github.com/junegunn/fzf#installation) for search functionality
- **Optional**: [Rye](https://github.com/astral-sh/rye) for development

## Installation

### Quick Install

```bash
# Clone the repository
git clone <repository_url>
cd samftp_cli

# Install with Rye (recommended)
rye sync
rye shell

# Or install with pip
pip install -e .
```

### First Run

On first launch, SAM-FTP CLI will guide you through an interactive setup wizard:

```bash
samftp
```

The wizard will help you:
1. Create the configuration file
2. Add your first server
3. Test the connection
4. Set your preferred media player

Alternatively, manually create `~/.samftp-cli.env`:

```bash
# Linux/macOS
cp .env.example ~/.samftp-cli.env

# Windows
copy .env.example %USERPROFILE%\.samftp-cli.env
```

## Usage

### Basic Usage

```bash
# Start the interactive browser
samftp

# Start with specific server
samftp --server "Movies"

# Use specific player
samftp --player mpv

# Launch TUI mode (experimental)
samftp --tui
```

### Configuration Management

```bash
# Run configuration wizard
samftp config

# Add a new server
samftp config-add

# Validate configuration
samftp config-validate

# Show config file location
samftp config-path
```

### Cache Management

```bash
# Show cache statistics
samftp cache-stats

# Clear all cache
samftp cache-clear
```

### Bookmarks

```bash
# List all bookmarks
samftp bookmarks-list

# In browser: Press 'a' to add bookmark at current location
# In browser: Press 'b' to view and navigate to bookmarks
```

### Interactive Controls

Once in the browser, use these commands:

| Key | Action |
|-----|--------|
| `0-N` | Select file or folder by number |
| `s` | Search (fuzzy find with fzf) |
| `m` | Multi-select mode (batch operations) |
| `p` | Play all media files as playlist |
| `d` | Download all files in directory |
| `a` | Add current location to bookmarks |
| `b` | View and navigate bookmarks |
| `c` | Change media player |
| `r` | Refresh (clear cache and reload) |
| `h` or `?` | Show help |
| `q` | Quit application |

### Batch Selection Mode

Press `m` to enter batch selection:

```
# Select individual items
1,3,5

# Select ranges
1-5,8,10-15

# Commands in batch mode
done   - Finish selection
clear  - Clear all selections
cancel - Exit without action
```

After selection, choose to:
1. Download selected files
2. Play selected media files
3. Cancel

## Configuration

### Server Configuration

Add servers to `~/.samftp-cli.env`:

```env
# Basic server
SERVER_1_NAME="English Movies"
SERVER_1_URL="http://172.16.50.7/Movies/"

# Server with authentication
SERVER_2_NAME="Private Server"
SERVER_2_URL="http://example.com/files/"
SERVER_2_USERNAME="myuser"
SERVER_2_PASSWORD="mypass"

# Server with preferred player
SERVER_3_NAME="Music"
SERVER_3_URL="http://music.server.com/"
SERVER_3_PREFERRED_PLAYER="mpv"
```

### Global Settings

```env
# Default media player (mpv, vlc, iina)
DEFAULT_PLAYER="mpv"

# Default download directory
DEFAULT_DOWNLOAD_DIR="/Users/you/Downloads"
```

## Development

### Setup

```bash
# Clone and setup
git clone <repository_url>
cd samftp_cli
rye sync

# Run from source
python -m samftp_cli.main

# Run tests (when available)
rye run pytest
```

### Code Quality

```bash
# Lint
rye lint

# Format
rye fmt

# Type check (if configured)
rye run mypy src
```

### Project Structure

```
src/samftp_cli/
├── main.py          # CLI entry point with Click framework
├── config.py        # Configuration management and wizard
├── ftp_client.py    # Async HTTP client with caching
├── ui.py            # Rich terminal UI components
├── player.py        # Media player integration
├── cache.py         # Directory listing cache manager
├── bookmarks.py     # Bookmark management
├── data_models.py   # Data classes and utilities
└── tui.py           # Textual TUI (experimental)
```

## Architecture

### Key Improvements (Phase 1)

1. **Async/Await**: Non-blocking operations with aiohttp
2. **Rich Formatting**: Beautiful terminal output with tables, panels, and colors
3. **Caching**: 5-minute TTL cache for directory listings
4. **Bookmarks**: Persistent favorite locations
5. **Player Persistence**: Remembers your preferred player
6. **Background Playback**: Non-blocking media playback
7. **Batch Operations**: Multi-select for downloads and playlists
8. **Better Errors**: Detailed error messages with retry logic
9. **Session Management**: Tracks state across navigation
10. **First-Run Experience**: Interactive setup wizard
11. **CLI Framework**: Click-based subcommands
12. **Authentication**: HTTP Basic Auth support
13. **Breadcrumbs**: Visual path navigation
14. **Download Management**: Configurable locations with progress bars

## Troubleshooting

### No servers configured
```bash
# Run the configuration wizard
samftp config
```

### fzf not found
```bash
# macOS
brew install fzf

# Ubuntu/Debian
sudo apt install fzf

# Fedora
sudo dnf install fzf
```

### Player not found
Install at least one media player:
- **mpv**: `brew install mpv` (macOS) or `sudo apt install mpv` (Linux)
- **VLC**: Download from [videolan.org](https://www.videolan.org/vlc/)
- **IINA**: Download from [iina.io](https://iina.io/) (macOS only)

### Cache issues
```bash
# Clear the cache
samftp cache-clear

# Check cache location and stats
samftp cache-stats
```

### Configuration file errors
If you encounter errors like "'NoneType' object has no attribute 'substitute'":

```bash
# The error is logged to a file for debugging
# Location (macOS): ~/Library/Logs/samftp-cli/error.log
# Location (Linux): ~/.local/state/samftp-cli/error.log
# Location (Windows): %LOCALAPPDATA%\samftp-cli\Logs\error.log

# Solutions:
# 1. Run the configuration wizard to recreate config
samftp config

# 2. Manually check config file for malformed variables
# Look for ${VARIABLE} references in ~/.samftp-cli.env

# 3. Delete config and restart
rm ~/.samftp-cli.env
samftp
```

## Roadmap

### Completed (Phase 1)
- ✅ Async operations with aiohttp
- ✅ Rich terminal formatting
- ✅ Caching system
- ✅ Bookmarks
- ✅ Batch selection
- ✅ Player persistence
- ✅ Background playback
- ✅ Authentication support
- ✅ Interactive setup wizard
- ✅ CLI framework with subcommands

### Future (Phase 2+)
- ⬜ File filtering and sorting
- ⬜ Search across entire server
- ⬜ Download queue management
- ⬜ Parallel downloads
- ⬜ Resume downloads
- ⬜ Subtitle auto-detection
- ⬜ Full TUI mode with mouse support
- ⬜ Playlist management and export
- ⬜ Command history
- ⬜ File information view

## License

MIT

## Author

Masnun Siam (echo@msiamn.dev)
