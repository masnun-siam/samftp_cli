"""
Textual-based TUI for SAM-FTP CLI.

This provides a rich terminal user interface with mouse support and modern interactions.
"""

from typing import List, Optional
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Input
from textual.binding import Binding
from rich.text import Text
from .data_models import Server


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
        self.search_query = ""
        self.all_files = []  # Will hold all files for filtering
        """
        Initialize TUI app.

        Args:
            servers: List of configured servers
            servers_name: Pre-selected server name (optional)
            player_override: Player override (optional)
        """
        super().__init__()
        self.servers = servers
        self.server_name = server_name
        self.player_override = player_override
        self.selected_server = None
        self.current_url = None

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

    def on_mount(self) -> None:
        """Called when app starts."""
        # Pre-select server if specified
        if self.server_name:
            for i, server in enumerate(self.servers):
                if server.name.lower() == self.server_name.lower():
                    self.selected_server = server
                    self.current_url = server.url
                    break

        # Load bookmarks
        self.load_bookmarks()

        # Focus search bar on mount
        self.query_one("#search-bar", Input).focus()

    def load_bookmarks(self) -> None:
        """Load and display bookmarks."""
        from .bookmarks import get_bookmark_manager

        bookmark_mgr = get_bookmark_manager()
        bookmarks = bookmark_mgr.list_bookmarks()

        bookmarks_list = self.query_one("#bookmarks-list", ListView)
        bookmarks_list.clear()

        for bm in bookmarks:
            bookmarks_list.append(ListItem(Label(f"★ {bm.name}")))

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Refresh current directory."""
        if self.current_url:
            # TODO: Implement directory refresh with cache invalidation
            pass

    def action_bookmarks(self) -> None:
        """Show bookmarks panel."""
        # TODO: Implement bookmarks panel
        pass

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Implement help screen
        pass

    def on_input_changed(self, event) -> None:
        """Update files list when search input changes."""
        input_widget = self.query_one("#search-bar", Input)
        self.search_query = input_widget.value
        self.update_files_list()

    def update_files_list(self) -> None:
        """Filter and update files ListView based on search query."""
        files_list = self.query_one("#files-list", ListView)
        files_list.clear()
        if not self.all_files:
            return
        query = self.search_query.lower()
        filtered = [f for f in self.all_files if query in f.name.lower()]
        for f in filtered:
            files_list.append(ListItem(Label(f.name)))

    def action_focus_search(self) -> None:
        """Focus the search bar."""
        self.query_one("#search-bar", Input).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle server or file selection."""
        # Check which ListView triggered the event
        if event.list_view.id == "servers-list":
            # Server selected
            selected_index = event.list_view.index
            if selected_index is not None and selected_index < len(self.servers):
                self.selected_server = self.servers[selected_index]
                self.current_url = self.selected_server.url
                self.notify(f"Selected server: {self.selected_server.name}")
                # TODO: Load directory listing for selected server
        elif event.list_view.id == "files-list":
            # File/folder selected
            # TODO: Implement file/folder navigation
            pass
        elif event.list_view.id == "bookmarks-list":
            # Bookmark selected
            # TODO: Implement bookmark navigation
            pass


# Note: This is a basic TUI skeleton. Full implementation would include:
# - Async directory loading
# - File/folder navigation with mouse and keyboard
# - Breadcrumb display
# - Context menus for files/folders
# - Download progress display
# - Player integration
# - Search functionality
# - Proper error handling and loading states
#
# Due to complexity and time constraints, the TUI mode is provided as a framework
# that can be expanded. The CLI mode (main_async) is fully functional and provides
# all Phase 1 improvements.
