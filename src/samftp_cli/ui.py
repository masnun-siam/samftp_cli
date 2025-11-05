import subprocess
from typing import List, Tuple, Optional, Set
from pyfzf.pyfzf import FzfPrompt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from .data_models import Server, Folder, File, parse_url_path
from .player import play_all_videos, VIDEO_EXTENSIONS, IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, is_media_file, get_file_type
from .bookmarks import get_bookmark_manager

console = Console()


def select_server(servers: List[Server]) -> Server:
    """Prompts the user to select a server."""
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  Select a Server  [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Index", style="cyan bold", justify="right")
    table.add_column("Server", style="green bold")

    for i, server in enumerate(servers):
        table.add_row(f"{i + 1}.", server.name)

    console.print(table)

    while True:
        choice = Prompt.ask(f"\n[bold]Enter your choice[/bold] (1-{len(servers)}, q to quit)")

        if choice.lower() == 'q':
            console.print("[yellow]Exiting...[/yellow]")
            exit(0)

        try:
            index = int(choice) - 1
            if 0 <= index < len(servers):
                return servers[index]
        except ValueError:
            pass

        console.print("[red]Invalid choice. Please try again.[/red]")


def display_breadcrumb(server_name: str, url: str):
    """Display breadcrumb navigation."""
    path_components = parse_url_path(url)

    breadcrumb = Text()
    breadcrumb.append("Server: ", style="dim")
    breadcrumb.append(server_name, style="bold cyan")

    if path_components:
        breadcrumb.append(" > ", style="dim")
        breadcrumb.append(" > ".join(path_components), style="bold white")

    console.print(Panel(breadcrumb, border_style="cyan"))


def display_directory_listing(folders: List[Folder], files: List[File],
                             current_url: str, selected_indices: Optional[Set[int]] = None) -> None:
    """
    Display directory contents with rich formatting.

    Args:
        folders: List of folders
        files: List of files
        current_url: Current directory URL
        selected_indices: Set of selected item indices (for batch mode)
    """
    items = folders + files

    # Check if current location is bookmarked
    bookmark_mgr = get_bookmark_manager()
    bookmark_name = bookmark_mgr.is_bookmarked(current_url)

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("✓", width=2, justify="center")  # Selection indicator
    table.add_column("Type", width=4, justify="center")
    table.add_column("Name")

    for i, item in enumerate(items):
        # Selection indicator
        check = "[green]✓[/green]" if selected_indices and i in selected_indices else ""

        if isinstance(item, Folder):
            # Folder styling
            icon = "📁"
            if item.name == "..":
                icon = "⬆️"
                style = "bold red"
            else:
                style = "bold green"

            table.add_row(str(i), check, icon, Text(item.name, style=style))

        else:
            # File styling based on type
            file_type = get_file_type(item.name)
            if file_type == "video":
                icon = "▶️"
                style = "bold blue"
            elif file_type == "audio":
                icon = "🎵"
                style = "bold yellow"
            elif file_type == "image":
                icon = "🖼️"
                style = "bold magenta"
            else:
                icon = "📄"
                style = "white"

            table.add_row(str(i), check, icon, Text(item.name, style=style))

    console.print(table)

    # Show counts and bookmark status
    info_text = Text()
    info_text.append(f"{len(folders)} folders, {len(files)} files", style="dim")

    if bookmark_name:
        info_text.append(f"  •  ", style="dim")
        info_text.append(f"★ {bookmark_name}", style="yellow")

    if selected_indices:
        info_text.append(f"  •  ", style="dim")
        info_text.append(f"{len(selected_indices)} selected", style="green bold")

    console.print(info_text)


def display_help():
    """Display available commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan bold", width=10)
    table.add_column("Description", style="white")

    commands = [
        ("0-N", "Select file or folder by number"),
        ("s", "Search (requires fzf)"),
        ("m", "Multi-select mode (batch select files)"),
        ("p", "Play all media files as playlist"),
        ("d", "Download all files in directory"),
        ("a", "Add current location to bookmarks"),
        ("b", "View bookmarks"),
        ("c", "Change media player"),
        ("r", "Refresh (reload directory)"),
        ("h/?", "Show this help"),
        ("q", "Quit application"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)
    console.print()


def parse_batch_selection(input_str: str, max_index: int) -> Set[int]:
    """
    Parse batch selection input (e.g., "1,3,5-8,10").

    Args:
        input_str: User input string
        max_index: Maximum valid index

    Returns:
        Set of selected indices
    """
    selected = set()

    parts = input_str.split(',')
    for part in parts:
        part = part.strip()

        if '-' in part:
            # Range (e.g., "5-8")
            try:
                start, end = part.split('-')
                start, end = int(start.strip()), int(end.strip())
                if 0 <= start <= max_index and 0 <= end <= max_index:
                    selected.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            # Single number
            try:
                index = int(part)
                if 0 <= index <= max_index:
                    selected.add(index)
            except ValueError:
                pass

    return selected


def batch_selection_mode(items: List) -> Set[int]:
    """
    Interactive batch selection mode.

    Args:
        items: List of items (folders + files)

    Returns:
        Set of selected indices
    """
    selected = set()

    console.print("\n[bold yellow]═══ Batch Selection Mode ═══[/bold yellow]")
    console.print("[dim]Select items by entering numbers, ranges (5-8), or comma-separated (1,3,5-8)[/dim]")
    console.print("[dim]Commands: done (finish), clear (clear selection), cancel (exit)[/dim]\n")

    while True:
        console.clear()
        console.print("[bold yellow]═══ Batch Selection Mode ═══[/bold yellow]\n")

        # Display items with selection indicators
        for i, item in enumerate(items):
            check = "[green]✓[/green]" if i in selected else "  "
            name = item.name
            console.print(f"{check} [{i}] {name}")

        console.print(f"\n[green]{len(selected)} items selected[/green]")

        choice = Prompt.ask("\n[bold]Enter selection or command[/bold]")

        if choice.lower() == 'done':
            break
        elif choice.lower() == 'clear':
            selected.clear()
            console.print("[yellow]Selection cleared[/yellow]")
        elif choice.lower() == 'cancel':
            return set()
        else:
            # Parse selection
            new_selected = parse_batch_selection(choice, len(items) - 1)
            selected.update(new_selected)

    return selected


def browse_directory(folders: List[Folder], files: List[File],
                    server_name: str, current_url: str) -> Tuple[str, Optional[int], Optional[Set[int]]]:
    """
    Displays the directory content and handles user interaction.

    Args:
        folders: List of folders
        files: List of files
        server_name: Server name for breadcrumb
        current_url: Current URL for breadcrumb

    Returns:
        Tuple of (action, selection_index, selected_indices_set)
        Actions: "quit", "select", "refresh", "download", "batch_download", "batch_play"
    """
    console.clear()
    display_breadcrumb(server_name, current_url)
    console.print()
    display_directory_listing(folders, files, current_url)

    items = folders + files

    console.print()
    choice = Prompt.ask(
        "[bold]Enter command[/bold] [dim](h for help)[/dim]"
    )

    # Handle commands
    if choice.lower() == 'q':
        return "quit", None, None

    if choice.lower() in ['h', '?']:
        display_help()
        Prompt.ask("[dim]Press Enter to continue[/dim]")
        return "refresh", None, None

    if choice.lower() == 'r':
        return "refresh", None, None

    if choice.lower() == 'p':
        play_all_videos(files)
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        return "refresh", None, None

    if choice.lower() == 'd':
        return "download", None, None

    if choice.lower() == 'c':
        from .player import change_player
        change_player()
        return "refresh", None, None

    if choice.lower() == 'a':
        # Add bookmark
        bookmark_mgr = get_bookmark_manager()
        bookmark_name = Prompt.ask("[bold]Enter bookmark name[/bold]")

        if bookmark_mgr.add_bookmark(bookmark_name, server_name, current_url):
            console.print(f"[green]✓ Bookmark '{bookmark_name}' added[/green]")
        else:
            console.print(f"[red]✗ Bookmark '{bookmark_name}' already exists[/red]")

        Prompt.ask("\n[dim]Press Enter to continue[/dim]")
        return "refresh", None, None

    if choice.lower() == 'b':
        # View bookmarks
        bookmark_mgr = get_bookmark_manager()
        bookmarks = bookmark_mgr.list_bookmarks()

        if not bookmarks:
            console.print("[yellow]No bookmarks saved[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            return "refresh", None, None

        console.print("\n[bold cyan]Bookmarks:[/bold cyan]")
        for i, bm in enumerate(bookmarks):
            console.print(f"  [cyan]{i + 1}.[/cyan] {bm.name} [dim]({bm.server})[/dim]")

        choice = Prompt.ask(f"\n[bold]Select bookmark (1-{len(bookmarks)}, or Enter to cancel)[/bold]")

        try:
            index = int(choice) - 1
            if 0 <= index < len(bookmarks):
                selected_bm = bookmarks[index]
                return "bookmark", None, {"url": selected_bm.url}
        except (ValueError, KeyError):
            pass

        return "refresh", None, None

    if choice.lower() == 'm':
        # Batch selection mode
        selected = batch_selection_mode(items)

        if not selected:
            console.print("[yellow]No items selected[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            return "refresh", None, None

        # Ask what to do with selection
        console.print(f"\n[green]{len(selected)} items selected[/green]")
        console.print("\n[bold]What would you like to do?[/bold]")
        console.print("  [cyan]1.[/cyan] Download selected files")
        console.print("  [cyan]2.[/cyan] Play selected media files")
        console.print("  [cyan]3.[/cyan] Cancel")

        action_choice = Prompt.ask("[bold]Enter choice[/bold] (1-3)", default="3")

        if action_choice == "1":
            return "batch_download", None, selected
        elif action_choice == "2":
            return "batch_play", None, selected
        else:
            return "refresh", None, None

    if choice.lower() == 's':
        # Search with fzf
        if not items:
            console.print("[yellow]No items to search[/yellow]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            return "refresh", None, None

        try:
            fzf = FzfPrompt()
            item_names = [item.name for item in items]
            selection = fzf.prompt(item_names, fzf_options="--height=40% --reverse")

            if selection:
                selected_index = item_names.index(selection[0])
                return "select", selected_index, None
            else:
                # User cancelled search
                console.print("[dim]Search cancelled[/dim]")
                return "refresh", None, None
        except FileNotFoundError:
            console.print("[red]Error: fzf command not found[/red]")
            console.print("[dim]Install fzf: brew install fzf (macOS) or see https://github.com/junegunn/fzf[/dim]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            return "refresh", None, None
        except Exception as e:
            console.print(f"[red]Search error: {e}[/red]")
            Prompt.ask("\n[dim]Press Enter to continue[/dim]")
            return "refresh", None, None

    # Try to parse as number (file/folder selection)
    try:
        selected_index = int(choice)
        if 0 <= selected_index < len(items):
            return "select", selected_index, None
    except ValueError:
        pass

    console.print("[red]Invalid command. Type 'h' for help.[/red]")
    Prompt.ask("\n[dim]Press Enter to continue[/dim]")
    return "refresh", None, None
