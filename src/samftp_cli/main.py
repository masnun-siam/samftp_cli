import os
import asyncio
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
import click
import aiohttp
from rich.console import Console
from platformdirs import user_log_dir
from .config import (
    load_servers_from_env,
    is_first_run,
    handle_first_run,
    run_config_wizard,
    add_server_interactive,
    validate_config,
    get_config_path
)
from .ftp_client import fetch_html_cached, get_download_directory, download_all_files, FTPClientError
from .ui import select_server, browse_directory
from .player import play_file, play_all_videos, get_player_preference
from .data_models import Folder, File, AppSession
from .cache import get_cache_manager
from .bookmarks import get_bookmark_manager

console = Console()


def log_error(error: Exception, context: str = ""):
    """
    Log error to file for debugging.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
    """
    try:
        log_dir = Path(user_log_dir("samftp-cli"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "error.log"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {timestamp}\n")
            if context:
                f.write(f"Context: {context}\n")
            f.write(f"Error Type: {type(error).__name__}\n")
            f.write(f"Error Message: {str(error)}\n")
            f.write(f"\nFull Traceback:\n")
            f.write(traceback.format_exc())
            f.write(f"\n{'='*80}\n")

        return str(log_file)
    except Exception:
        return None


@click.group(invoke_without_command=True)
@click.option('--tui', is_flag=True, help='Launch in TUI mode')
@click.option('--server', '-s', help='Pre-select server by name')
@click.option('--player', '-p', help='Override default player (mpv, vlc, iina)')
@click.option('--config', help='Path to custom config file')
@click.pass_context
def cli(ctx, tui, server, player, config):
    """
    SAM-FTP CLI - Browse and play media from SAM-FTP servers.

    Run without arguments to start the interactive browser.
    Use subcommands for configuration and management.
    """
    # If a subcommand was invoked, don't run the main app
    if ctx.invoked_subcommand is not None:
        return

    if tui:
        # Launch TUI mode
        launch_tui(server_name=server, player_override=player)
    else:
        # Launch standard CLI mode
        try:
            asyncio.run(main_async(server_name=server, player_override=player))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user. Exiting...[/yellow]")
            sys.exit(0)


@cli.command()
def config():
    """Run the configuration wizard."""
    run_config_wizard()


@cli.command('config-add')
def config_add():
    """Add a new server to configuration."""
    add_server_interactive()


@cli.command('config-validate')
def config_validate():
    """Validate the configuration file."""
    is_valid, errors = validate_config()

    if is_valid:
        console.print("[green]✓ Configuration is valid[/green]")
    else:
        console.print("[red]✗ Configuration has errors:[/red]")
        for error in errors:
            console.print(f"  [red]•[/red] {error}")
        sys.exit(1)


@cli.command('config-path')
def config_path():
    """Show the path to the configuration file."""
    path = get_config_path()
    console.print(f"[cyan]Configuration file:[/cyan] {path}")

    if path.exists():
        console.print(f"[green]✓ File exists[/green]")
    else:
        console.print(f"[yellow]⚠ File does not exist[/yellow]")


@cli.command('cache-clear')
def cache_clear():
    """Clear all cached directory listings."""
    cache = get_cache_manager()
    cache.clear_all_cache()
    console.print("[green]✓ Cache cleared[/green]")


@cli.command('cache-stats')
def cache_stats():
    """Show cache statistics."""
    cache = get_cache_manager()
    stats = cache.get_cache_stats()

    console.print("\n[bold cyan]Cache Statistics:[/bold cyan]")
    console.print(f"  Location: [dim]{stats['cache_location']}[/dim]")
    console.print(f"  Total entries: {stats['total_entries']}")
    console.print(f"  Valid entries: [green]{stats['valid_entries']}[/green]")
    console.print(f"  Expired entries: [yellow]{stats['expired_entries']}[/yellow]")
    console.print(f"  Cache size: {stats['cache_size_kb']:.2f} KB")
    console.print(f"  TTL: {stats['ttl_seconds']}s\n")


@cli.command('bookmarks-list')
def bookmarks_list():
    """List all bookmarks."""
    bookmark_mgr = get_bookmark_manager()
    bookmarks = bookmark_mgr.list_bookmarks()

    if not bookmarks:
        console.print("[yellow]No bookmarks saved[/yellow]")
        return

    console.print("\n[bold cyan]Bookmarks:[/bold cyan]")
    for bm in bookmarks:
        console.print(f"  [cyan]★[/cyan] {bm.name} [dim]({bm.server})[/dim]")
        console.print(f"    {bm.url}")
    console.print()


async def main_async(server_name: Optional[str] = None, player_override: Optional[str] = None):
    """
    Main async application logic.

    Args:
        server_name: Pre-selected server name (optional)
        player_override: Player override from CLI flag (optional)
    """
    try:
        # Check first run
        if is_first_run():
            if not handle_first_run():
                console.print("[yellow]Exiting. Run 'samftp config' to set up servers later.[/yellow]")
                return

        # Load servers
        servers = load_servers_from_env()
        if not servers:
            console.print("[red]No servers configured. Run 'samftp config' to add servers.[/red]")
            return
    except AttributeError as e:
        if "'NoneType' object has no attribute 'substitute'" in str(e):
            log_file = log_error(e, "Loading servers from config")
            console.print("\n[red]Error: Configuration file corrupted.[/red]")
            console.print("[yellow]Please run 'samftp config' to recreate your configuration.[/yellow]")
            if log_file:
                console.print(f"[dim]Error logged to: {log_file}[/dim]\n")
            return
        raise

    # Select server
    if server_name:
        # Find server by name
        selected_server = next((s for s in servers if s.name.lower() == server_name.lower()), None)
        if not selected_server:
            console.print(f"[red]Server '{server_name}' not found[/red]")
            console.print("[dim]Available servers:[/dim]")
            for s in servers:
                console.print(f"  • {s.name}")
            return
    else:
        selected_server = select_server(servers)

    # Initialize session
    session = AppSession(
        selected_server=selected_server,
        selected_player=player_override,
        history=[]
    )

    current_url = selected_server.url

    # Create aiohttp session for connection pooling
    async with aiohttp.ClientSession() as http_session:
        # Main navigation loop
        while True:
            try:
                # Prepare authentication if needed
                auth = None
                if selected_server.username and selected_server.password:
                    auth = aiohttp.BasicAuth(
                        selected_server.username,
                        selected_server.password
                    )

                # Fetch directory listing (with caching)
                try:
                    folders, files = await fetch_html_cached(http_session, current_url, auth)
                except FTPClientError as e:
                    console.print(f"[red]Error: {e}[/red]")
                    console.print("[yellow]Press Enter to retry, or Ctrl+C to exit[/yellow]")
                    input()
                    continue

                # Update session
                session.current_url = current_url

                # Browse directory and get user action
                action, selected_index, batch_data = browse_directory(
                    folders,
                    files,
                    selected_server.name,
                    current_url
                )

                if action == "quit":
                    break

                if action == "refresh":
                    # Force refresh (bypass cache)
                    cache = get_cache_manager()
                    cache.invalidate_cache(current_url)
                    continue

                if action == "bookmark":
                    # Navigate to bookmarked URL
                    if batch_data and "url" in batch_data:
                        current_url = batch_data["url"]
                        # Add to history
                        session.history.append(current_url)
                    continue

                if action == "download":
                    # Download all files
                    default_dir = session.download_directory or os.getcwd()
                    download_dir = get_download_directory(default_dir)
                    session.download_directory = download_dir

                    # Prepare auth tuple for sync download function
                    auth_tuple = None
                    if selected_server.username and selected_server.password:
                        auth_tuple = (selected_server.username, selected_server.password)

                    download_all_files(files, download_dir, auth_tuple)

                    console.print("\n[dim]Press Enter to continue[/dim]")
                    input()
                    continue

                if action == "batch_download":
                    # Download selected files
                    if batch_data:
                        items = folders + files
                        selected_files = [items[i] for i in batch_data if i < len(items) and isinstance(items[i], File)]

                        if not selected_files:
                            console.print("[yellow]No files selected for download[/yellow]")
                            console.print("\n[dim]Press Enter to continue[/dim]")
                            input()
                            continue

                        default_dir = session.download_directory or os.getcwd()
                        download_dir = get_download_directory(default_dir)
                        session.download_directory = download_dir

                        auth_tuple = None
                        if selected_server.username and selected_server.password:
                            auth_tuple = (selected_server.username, selected_server.password)

                        download_all_files(selected_files, download_dir, auth_tuple)

                        console.print("\n[dim]Press Enter to continue[/dim]")
                        input()
                    continue

                if action == "batch_play":
                    # Play selected files
                    if batch_data:
                        items = folders + files
                        selected_files = [items[i] for i in batch_data if i < len(items) and isinstance(items[i], File)]

                        media_files = [f for f in selected_files if f.url.endswith(
                            ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v',
                             '.mp3', '.flac', '.m4a', '.wav', '.ogg', '.aac')
                        )]

                        if not media_files:
                            console.print("[yellow]No media files selected[/yellow]")
                            console.print("\n[dim]Press Enter to continue[/dim]")
                            input()
                            continue

                        play_all_videos(media_files, player=session.selected_player)
                        console.print("\n[dim]Press Enter to continue[/dim]")
                        input()
                    continue

                if action == "select" and selected_index is not None:
                    items = folders + files
                    selected_item = items[selected_index]

                    if isinstance(selected_item, Folder):
                        # Navigate to folder
                        session.history.append(current_url)
                        current_url = selected_item.url
                    elif isinstance(selected_item, File):
                        # Play/view file
                        play_file(selected_item, player=session.selected_player)
                        console.print("\n[dim]Press Enter to continue[/dim]")
                        input()

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Exiting...[/yellow]")
                break
            except AttributeError as e:
                if "'NoneType' object has no attribute 'substitute'" in str(e):
                    log_file = log_error(e, "Navigation loop - dotenv substitution error")
                    console.print("\n[red]Error: Configuration file corrupted.[/red]")
                    console.print("[yellow]This error occurs when dotenv encounters malformed variable references.[/yellow]")
                    console.print(f"[dim]Config file: {get_config_path()}[/dim]\n")
                    console.print("[cyan]Solutions:[/cyan]")
                    console.print("  1. Run [bold]samftp config[/bold] to recreate configuration")
                    console.print("  2. Delete config file and restart")
                    console.print("  3. Manually check for ${VARIABLE} references in config\n")
                    if log_file:
                        console.print(f"[dim]Error details logged to: {log_file}[/dim]\n")
                    break
                else:
                    log_file = log_error(e, "Unexpected AttributeError in navigation loop")
                    console.print(f"[red]Unexpected error: {e}[/red]")
                    if log_file:
                        console.print(f"[dim]Error logged to: {log_file}[/dim]")
                    console.print("[yellow]Press Enter to continue, or Ctrl+C to exit[/yellow]")
                    input()
            except Exception as e:
                log_file = log_error(e, "Unexpected exception in navigation loop")
                console.print(f"[red]Unexpected error: {e}[/red]")
                if log_file:
                    console.print(f"[dim]Error logged to: {log_file}[/dim]")
                console.print("[yellow]Press Enter to continue, or Ctrl+C to exit[/yellow]")
                input()


def launch_tui(server_name: Optional[str] = None, player_override: Optional[str] = None):
    """
    Launch TUI mode.

    Args:
        server_name: Pre-selected server name (optional)
        player_override: Player override from CLI flag (optional)
    """
    try:
        from .tui import SamFTPApp

        # Check first run
        if is_first_run():
            if not handle_first_run():
                console.print("[yellow]Exiting. Run 'samftp config' to set up servers later.[/yellow]")
                return

        # Load servers
        servers = load_servers_from_env()
        if not servers:
            console.print("[red]No servers configured. Run 'samftp config' to add servers.[/red]")
            return

        # Create and run TUI app
        app = SamFTPApp(servers=servers, server_name=server_name, player_override=player_override)
        app.run()

    except ImportError as e:
        console.print(f"[red]Error: TUI dependencies not installed: {e}[/red]")
        console.print("[yellow]Install textual: pip install textual[/yellow]")
    except Exception as e:
        console.print(f"[red]Error launching TUI: {e}[/red]")


def tui_entry():
    """Entry point for samftp-tui command."""
    launch_tui()


def main():
    """Legacy entry point for backward compatibility."""
    cli()


if __name__ == "__main__":
    cli()
