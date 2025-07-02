# SAM-FTP CLI

A command-line interface to browse and play media from SAM-FTP servers.

## Features

- Browse FTP server directories.
- Play videos and view images directly from the command line using `mpv`, `VLC`, or `IINA`.
- Create playlists on the fly to watch all videos in a folder.
- Fuzzy search for files in the current directory using `fzf`.
- Server configurations are managed through an `.env` file.

## Prerequisites

- Python 3.8+
- [mpv](https://mpv.io/installation/), [VLC](https://www.videolan.org/vlc/), or [IINA](https://iina.io/) for playing media.
- [fzf](https://github.com/junegunn/fzf#installation) for search functionality.
- [Rye](https://github.com/astral-sh/rye) for dependency management.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd samftp_cli
    ```

2.  **Create and edit the configuration file:**
    Copy the `.env.example` file to your home directory and rename it to `.samftp-cli.env`.

    -   **On Linux or macOS:**
        ```bash
        cp .env.example ~/.samftp-cli.env
        ```

    -   **On Windows:**
        ```powershell
        copy .env.example $HOME\\.samftp-cli.env
        ```
    
    Now, open `~/.samftp-cli.env` (or `%USERPROFILE%\\.samftp-cli.env` on Windows) and add your server details.

3.  **Run the installation script:**
    This will install dependencies and make the `samftp` command globally available.

    -   **On Linux or macOS:**
        ```bash
        chmod +x install.sh
        ./install.sh
        ```

    -   **On Windows:**
        ```bat
        install.bat
        ```

## Usage

Once installed, you can run the application from any directory:

```bash
samftp
```

You will be prompted to select a server, and then you can browse the directories.

### Controls

-   `0-N`: Select a file or folder by number.
-   `s`: Search for a file or folder in the current directory (requires `fzf`).
-   `p`: Play all video files in the current directory as a playlist.
-   `q`: Quit the application.

## Development

This project uses `ruff` for linting and formatting, managed through Rye.

-   **Lint:** `rye lint`
-   **Format:** `rye fmt` 