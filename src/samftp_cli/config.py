import os
import time
from pathlib import Path
from typing import List, Optional, Tuple
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.prompt import Prompt, Confirm
from .data_models import Server
import requests

console = Console()


def get_config_path() -> Path:
    """Returns the path to the configuration file in the user's home directory."""
    return Path.home() / ".samftp-cli.env"


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    if not (url.startswith('http://') or url.startswith('https://')):
        return False, "URL must start with http:// or https://"

    # Basic URL structure check
    if '//' not in url or len(url) < 10:
        return False, "URL appears to be malformed"

    return True, None


def test_server_connection(server: Server, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Test if server is reachable.

    Args:
        server: Server to test
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (is_reachable, error_message)
    """
    try:
        auth = None
        if server.username and server.password:
            auth = (server.username, server.password)

        response = requests.get(server.url, timeout=timeout, auth=auth, allow_redirects=True)

        if response.status_code == 401:
            return False, "Authentication required - invalid or missing credentials"
        elif response.status_code == 403:
            return False, "Access forbidden - check permissions"
        elif response.status_code == 404:
            return False, "Server not found - check URL"
        elif response.status_code >= 500:
            return False, f"Server error (HTTP {response.status_code})"
        elif response.status_code >= 400:
            return False, f"Client error (HTTP {response.status_code})"

        return True, None

    except requests.exceptions.ConnectionError:
        return False, "Connection failed - check network and server address"
    except requests.exceptions.Timeout:
        return False, f"Connection timeout after {timeout} seconds"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"


def load_servers_from_env() -> List[Server]:
    """
    Loads server configurations from the config file (~/.samftp-cli.env).
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            load_dotenv(dotenv_path=config_path)
        except AttributeError as e:
            if "'NoneType' object has no attribute 'substitute'" in str(e):
                console.print("\n[red]Error: Configuration file appears to be corrupted.[/red]")
                console.print("[yellow]This can happen if there are malformed variable references in the file.[/yellow]")
                console.print(f"[dim]Config location: {config_path}[/dim]\n")
                console.print("[cyan]Try one of these solutions:[/cyan]")
                console.print("  1. Run: [bold]samftp config[/bold] to recreate the configuration")
                console.print("  2. Manually edit the file to remove any ${VARIABLE} references")
                console.print("  3. Delete the file and run the setup wizard again\n")
                return []
            raise
        except Exception as e:
            console.print(f"\n[red]Error loading configuration: {e}[/red]")
            console.print(f"[dim]Config location: {config_path}[/dim]\n")
            return []

    servers: List[Server] = []
    i = 1
    while True:
        name = os.getenv(f"SERVER_{i}_NAME")
        url = os.getenv(f"SERVER_{i}_URL")

        if not all([name, url]):
            break

        # Load optional authentication fields
        username = os.getenv(f"SERVER_{i}_USERNAME")
        password = os.getenv(f"SERVER_{i}_PASSWORD")
        preferred_player = os.getenv(f"SERVER_{i}_PREFERRED_PLAYER")

        servers.append(Server(
            name=name,
            url=url,
            username=username,
            password=password,
            preferred_player=preferred_player
        ))
        i += 1

    if not servers:
        console.print("\n[yellow]Warning: No server configurations found.[/yellow]")
        console.print(f"[dim]Configuration file: {config_path}[/dim]\n")

    return servers


def get_default_player() -> Optional[str]:
    """Get default player from config."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            load_dotenv(dotenv_path=config_path)
        except (AttributeError, Exception):
            return None
    return os.getenv("DEFAULT_PLAYER")


def set_default_player(player: str) -> bool:
    """
    Save default player to config.

    Args:
        player: Player name (mpv, vlc, iina)

    Returns:
        True if saved successfully
    """
    config_path = get_config_path()

    try:
        if not config_path.exists():
            config_path.touch()

        result = set_key(str(config_path), "DEFAULT_PLAYER", player)
        if result and result[0]:
            return True
        return False
    except AttributeError as e:
        if "'NoneType' object has no attribute 'substitute'" in str(e):
            console.print(f"[red]Error: Config file corrupted. Please run 'samftp config' to recreate it.[/red]")
        else:
            console.print(f"[red]Error saving player preference: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error saving player preference: {e}[/red]")
        return False


def get_default_download_dir() -> Optional[str]:
    """Get default download directory from config."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            load_dotenv(dotenv_path=config_path)
        except (AttributeError, Exception):
            return None
    return os.getenv("DEFAULT_DOWNLOAD_DIR")


def set_default_download_dir(directory: str) -> bool:
    """
    Save default download directory to config.

    Args:
        directory: Directory path

    Returns:
        True if saved successfully
    """
    config_path = get_config_path()

    try:
        if not config_path.exists():
            config_path.touch()

        result = set_key(str(config_path), "DEFAULT_DOWNLOAD_DIR", directory)
        if result and result[0]:
            return True
        return False
    except AttributeError as e:
        if "'NoneType' object has no attribute 'substitute'" in str(e):
            console.print(f"[red]Error: Config file corrupted. Please run 'samftp config' to recreate it.[/red]")
        else:
            console.print(f"[red]Error saving download directory: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error saving download directory: {e}[/red]")
        return False


def validate_config() -> Tuple[bool, List[str]]:
    """
    Validate the configuration file.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    config_path = get_config_path()

    if not config_path.exists():
        return False, ["Configuration file not found"]

    servers = load_servers_from_env()

    if not servers:
        return False, ["No servers configured"]

    errors = []

    for server in servers:
        # Validate URL
        is_valid, error = validate_url(server.url)
        if not is_valid:
            errors.append(f"Server '{server.name}': {error}")

        # Check for incomplete auth (username without password or vice versa)
        if (server.username and not server.password) or (server.password and not server.username):
            errors.append(f"Server '{server.name}': Both username and password required for authentication")

    if errors:
        return False, errors

    return True, []


def add_server_interactive() -> bool:
    """
    Interactive wizard to add a single server.

    Returns:
        True if server added successfully
    """
    console.print("\n[bold cyan]Add New Server[/bold cyan]\n")

    # Get server name
    name = Prompt.ask("[bold]Server name[/bold]")
    if not name:
        console.print("[red]Server name cannot be empty[/red]")
        return False

    # Get URL
    url = Prompt.ask("[bold]Server URL[/bold]")

    # Validate URL
    is_valid, error = validate_url(url)
    if not is_valid:
        console.print(f"[red]Invalid URL: {error}[/red]")
        return False

    # Ask about authentication
    needs_auth = Confirm.ask("[bold]Does this server require authentication?[/bold]", default=False)

    username = None
    password = None

    if needs_auth:
        username = Prompt.ask("[bold]Username[/bold]")
        password = Prompt.ask("[bold]Password[/bold]", password=True)

    # Create server object
    server = Server(name=name, url=url, username=username, password=password)

    # Test connection
    console.print("\n[cyan]Testing connection...[/cyan]")
    is_reachable, error = test_server_connection(server)

    if not is_reachable:
        console.print(f"[yellow]Warning: {error}[/yellow]")
        should_continue = Confirm.ask("[bold]Add server anyway?[/bold]", default=False)
        if not should_continue:
            return False
    else:
        console.print("[green]✓ Connection successful![/green]")

    # Save to config
    config_path = get_config_path()

    # Load existing servers to get next index
    existing_servers = load_servers_from_env()
    next_index = len(existing_servers) + 1

    try:
        if not config_path.exists():
            config_path.touch()

        result1 = set_key(str(config_path), f"SERVER_{next_index}_NAME", name)
        result2 = set_key(str(config_path), f"SERVER_{next_index}_URL", url)

        if username:
            set_key(str(config_path), f"SERVER_{next_index}_USERNAME", username)
        if password:
            set_key(str(config_path), f"SERVER_{next_index}_PASSWORD", password)

        if result1 and result1[0] and result2 and result2[0]:
            console.print(f"\n[green]✓ Server '{name}' added successfully![/green]\n")
            return True
        else:
            console.print("[red]Error: Failed to save server configuration[/red]")
            return False

    except AttributeError as e:
        if "'NoneType' object has no attribute 'substitute'" in str(e):
            console.print(f"[red]Error: Config file corrupted.[/red]")
            console.print(f"[yellow]Backup your current config and recreate it with 'samftp config'[/yellow]")
        else:
            console.print(f"[red]Error saving configuration: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]")
        return False


def run_config_wizard(skip_test: bool = False) -> bool:
    """
    Interactive configuration wizard for initial setup.

    Args:
        skip_test: Skip connection testing

    Returns:
        True if at least one server was configured
    """
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  SAM-FTP CLI Configuration Wizard  [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    console.print("[dim]Let's set up your FTP servers.\n[/dim]")

    servers_added = 0

    while True:
        if add_server_interactive():
            servers_added += 1

        console.print()
        add_another = Confirm.ask("[bold]Add another server?[/bold]", default=True)

        if not add_another:
            break

    if servers_added > 0:
        console.print(f"\n[green]✓ Configuration complete! Added {servers_added} server(s).[/green]")
        console.print(f"[dim]Configuration saved to: {get_config_path()}[/dim]\n")
        return True
    else:
        console.print("\n[yellow]No servers were added.[/yellow]\n")
        return False


def is_first_run() -> bool:
    """Check if this is the first run (no config file exists or no servers configured)."""
    config_path = get_config_path()

    if not config_path.exists():
        return True

    servers = load_servers_from_env()
    return len(servers) == 0


def handle_first_run() -> bool:
    """
    Handle first-run experience.

    Returns:
        True if setup completed successfully, False if user quit
    """
    console.print("\n[bold yellow]Welcome to SAM-FTP CLI![/bold yellow]\n")
    console.print("[dim]It looks like this is your first time running the application.[/dim]")
    console.print("[dim]Let's get you set up with some servers.\n[/dim]")

    should_setup = Confirm.ask("[bold]Would you like to configure servers now?[/bold]", default=True)

    if not should_setup:
        console.print("\n[yellow]Setup skipped. You can run the wizard later with:[/yellow]")
        console.print("[bold cyan]  samftp config add[/bold cyan]\n")
        return False

    return run_config_wizard()
