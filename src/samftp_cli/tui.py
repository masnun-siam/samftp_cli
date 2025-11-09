"""
Textual-based TUI for SAM-FTP CLI.

This provides a rich terminal user interface with mouse support and modern interactions.
"""

import asyncio
from typing import List, Optional
import aiohttp
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Input
from textual.binding import Binding
from textual.events import Mount
from textual import work
from rich.text import Text
from .data_models import Server, File, Folder
from .ftp_client import fetch_html_cached
from .cache import get_cache_manager
from .player import play_file


class SamFTPApp(App):
    """SAM-FTP TUI Application."""

    TITLE = "SAM-FTP CLI"
    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        color: $text;
    }

    Footer {
        background: $panel;
    }

    #main-container {
        layout: horizontal;
    }

    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
    }

    #content {
        width: 1fr;
    }

    .section-title {
        background: $primary;
        color: $text;
        padding: 1;
        text-style: bold;
    }

    ListView {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("b", "bookmarks", "Bookmarks", show=True),
        Binding("h", "help", "Help", show=True),
        Binding("/", "focus_search", "Search", show=True),
    ]

    def __init__(self, servers: List[Server], server_name: Optional[str] = None,
                 player_override: Optional[str] = None):
        """
        Initialize TUI app.

        Args:
            servers: List of configured servers
            server_name: Pre-selected server name (optional)
            player_override: Player override (optional)
        """
        super().__init__()
        self.servers = servers
        self.server_name = server_name
        self.player_override = player_override
        self.selected_server: Optional[Server] = None
        self.current_url: Optional[str] = None
        self.search_query = ""
        self.all_files: List[File] = []
        self.all_folders: List[Folder] = []
        self.http_session: Optional[aiohttp.ClientSession] = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Container(id="main-container"):
            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("Servers", classes="section-title")
                yield ListView(
                    *[ListItem(Label(s.name)) for s in self.servers],
                    id="servers-list"
                )

                yield Static("Bookmarks", classes="section-title")
                yield ListView(id="bookmarks-list")

            # Main content area
            with Vertical(id="content"):
                yield Static("Directory Browser", classes="section-title")
                yield Input(placeholder="Search files...", id="search-bar")
                yield ListView(id="files-list")

        yield Footer()

    async def on_mount(self) -> None:
        """Called when app starts."""
        # Create HTTP session
        self.http_session = aiohttp.ClientSession()

        # Pre-select server if specified
        if self.server_name:
            for i, server in enumerate(self.servers):
                if server.name.lower() == self.server_name.lower():
                    self.selected_server = server
                    self.current_url = server.url
                    # Load directory for pre-selected server
                    await self.load_directory()
                    break

        # Load bookmarks
        self.load_bookmarks()

        # Focus search bar on mount
        self.query_one("#search-bar", Input).focus()

    async def on_unmount(self) -> None:
        """Called when app is closing."""
        if self.http_session:
            await self.http_session.close()

    def load_bookmarks(self) -> None:
        """Load and display bookmarks."""
        from .bookmarks import get_bookmark_manager

        bookmark_mgr = get_bookmark_manager()
        bookmarks = bookmark_mgr.list_bookmarks()

        bookmarks_list = self.query_one("#bookmarks-list", ListView)
        bookmarks_list.clear()

        for bm in bookmarks:
            bookmarks_list.append(ListItem(Label(f"★ {bm.name}")))

    async def load_directory(self) -> None:
        """Load directory listing for current URL."""
        if not self.current_url or not self.http_session:
            return

        try:
            # Prepare authentication if needed
            auth = None
            if self.selected_server and self.selected_server.username and self.selected_server.password:
                auth = aiohttp.BasicAuth(
                    self.selected_server.username,
                    self.selected_server.password
                )

            # Fetch directory listing
            folders, files = await fetch_html_cached(self.http_session, self.current_url, auth)

            # Store for filtering
            self.all_folders = folders
            self.all_files = files

            # Update files list
            self.update_files_list()

        except Exception as e:
            self.notify(f"Error loading directory: {e}", severity="error")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Refresh current directory."""
        if self.current_url:
            # Invalidate cache and reload
            cache = get_cache_manager()
            cache.invalidate_cache(self.current_url)
            asyncio.create_task(self.load_directory())

    def action_bookmarks(self) -> None:
        """Show bookmarks panel."""
        bookmarks_list = self.query_one("#bookmarks-list", ListView)
        bookmarks_list.focus()

    def action_help(self) -> None:
        """Show help screen."""
        help_text = """
        Keyboard Shortcuts:
        q - Quit application
        r - Refresh current directory
        b - Focus bookmarks
        h - Show this help
        / - Focus search bar

        Navigate using arrow keys or mouse.
        """
        self.notify(help_text.strip())

    def on_input_changed(self, event) -> None:
        """Update files list when search input changes."""
        input_widget = self.query_one("#search-bar", Input)
        self.search_query = input_widget.value
        self.update_files_list()

    def update_files_list(self) -> None:
        """Filter and update files ListView based on search query."""
        files_list = self.query_one("#files-list", ListView)
        files_list.clear()

        query = self.search_query.lower()

        # Filter and add folders
        filtered_folders = [f for f in self.all_folders if query in f.name.lower()]
        for folder in filtered_folders:
            files_list.append(ListItem(Label(f"📁 {folder.name}")))

        # Filter and add files
        filtered_files = [f for f in self.all_files if query in f.name.lower()]
        for file in filtered_files:
            # Add icon based on file type
            icon = "▶️" if file.name.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')) else \
                   "🎵" if file.name.endswith(('.mp3', '.flac', '.m4a', '.wav')) else \
                   "🖼️" if file.name.endswith(('.jpg', '.jpeg', '.png', '.gif')) else "📄"
            files_list.append(ListItem(Label(f"{icon} {file.name}")))

    def action_focus_search(self) -> None:
        """Focus the search bar."""
        self.query_one("#search-bar", Input).focus()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle server or file selection."""
        # Check which ListView triggered the event
        if event.list_view.id == "servers-list":
            # Server selected
            selected_index = event.list_view.index
            if selected_index is not None and selected_index < len(self.servers):
                self.selected_server = self.servers[selected_index]
                self.current_url = self.selected_server.url
                self.notify(f"Selected server: {self.selected_server.name}")
                # Load directory listing for selected server
                await self.load_directory()

        elif event.list_view.id == "files-list":
            # File/folder selected
            selected_index = event.list_view.index
            if selected_index is None:
                return

            # Combine folders and files (filtered)
            query = self.search_query.lower()
            filtered_folders = [f for f in self.all_folders if query in f.name.lower()]
            filtered_files = [f for f in self.all_files if query in f.name.lower()]
            all_items = filtered_folders + filtered_files

            if selected_index < len(all_items):
                selected_item = all_items[selected_index]

                if isinstance(selected_item, Folder):
                    # Navigate to folder
                    self.current_url = selected_item.url
                    await self.load_directory()
                    self.notify(f"Navigated to: {selected_item.name}")

                elif isinstance(selected_item, File):
                    # Play/view file
                    try:
                        play_file(selected_item, player=self.player_override)
                        self.notify(f"Playing: {selected_item.name}")
                    except Exception as e:
                        self.notify(f"Error playing file: {e}", severity="error")

        elif event.list_view.id == "bookmarks-list":
            # Bookmark selected
            from .bookmarks import get_bookmark_manager
            bookmark_mgr = get_bookmark_manager()
            bookmarks = bookmark_mgr.list_bookmarks()

            selected_index = event.list_view.index
            if selected_index is not None and selected_index < len(bookmarks):
                bookmark = bookmarks[selected_index]
                # Find the server for this bookmark
                for server in self.servers:
                    if server.name == bookmark.server:
                        self.selected_server = server
                        self.current_url = bookmark.url
                        await self.load_directory()
                        self.notify(f"Opened bookmark: {bookmark.name}")
                        break
