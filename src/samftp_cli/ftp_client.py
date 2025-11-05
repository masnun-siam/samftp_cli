import os
import sys
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Tuple, Optional
import aiohttp
import aiofiles
from rich.console import Console
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from .data_models import Folder, File, format_file_size
from .cache import get_cache_manager

console = Console()


# Custom exceptions
class FTPClientError(Exception):
    """Base exception for FTP client errors."""
    pass


class ConnectionError(FTPClientError):
    """Raised when connection to server fails."""
    pass


class ServerError(FTPClientError):
    """Raised when server returns 5xx error."""
    pass


class AuthenticationError(FTPClientError):
    """Raised when authentication fails."""
    pass


class NotFoundError(FTPClientError):
    """Raised when resource not found (404)."""
    pass


class TimeoutError(FTPClientError):
    """Raised when request times out."""
    pass


async def fetch_html_async(session: aiohttp.ClientSession, url: str,
                          auth: Optional[aiohttp.BasicAuth] = None,
                          timeout: int = 30) -> bytes:
    """
    Fetches HTML content from a given URL asynchronously.

    Args:
        session: aiohttp client session
        url: URL to fetch
        auth: Optional authentication
        timeout: Request timeout in seconds

    Returns:
        HTML content as bytes

    Raises:
        ConnectionError: Network connection failed
        TimeoutError: Request timeout
        AuthenticationError: Authentication required/failed
        NotFoundError: Resource not found
        ServerError: Server error occurred
    """
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with session.get(url, auth=auth, timeout=timeout_obj, allow_redirects=True) as response:
            if response.status == 401:
                raise AuthenticationError("Authentication required - invalid or missing credentials")
            elif response.status == 403:
                raise AuthenticationError("Access forbidden - check permissions")
            elif response.status == 404:
                raise NotFoundError(f"Resource not found: {url}")
            elif response.status >= 500:
                raise ServerError(f"Server error (HTTP {response.status})")
            elif response.status >= 400:
                raise ConnectionError(f"Client error (HTTP {response.status})")

            response.raise_for_status()
            return await response.read()

    except asyncio.TimeoutError:
        raise TimeoutError(f"Request timeout after {timeout} seconds")
    except aiohttp.ClientConnectorError as e:
        raise ConnectionError(f"Connection failed - check network and server address: {e}")
    except aiohttp.ClientError as e:
        raise ConnectionError(f"Request error: {e}")


async def fetch_html_with_retry(session: aiohttp.ClientSession, url: str,
                                auth: Optional[aiohttp.BasicAuth] = None,
                                max_retries: int = 3) -> bytes:
    """
    Fetch HTML with automatic retry on failure.

    Args:
        session: aiohttp client session
        url: URL to fetch
        auth: Optional authentication
        max_retries: Maximum number of retry attempts

    Returns:
        HTML content as bytes
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return await fetch_html_async(session, url, auth)
        except (ConnectionError, TimeoutError, ServerError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                console.print(f"[yellow]Attempt {attempt + 1} failed, retrying in {wait_time}s...[/yellow]")
                await asyncio.sleep(wait_time)
            else:
                console.print(f"[red]All {max_retries} attempts failed[/red]")

    raise last_error


def fetch_html(url: str, auth: Optional[Tuple[str, str]] = None) -> bytes:
    """
    Synchronous wrapper for fetch_html_async (for backward compatibility).

    Args:
        url: URL to fetch
        auth: Optional tuple of (username, password)

    Returns:
        HTML content as bytes
    """
    async def _fetch():
        auth_obj = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with aiohttp.ClientSession() as session:
            return await fetch_html_with_retry(session, url, auth_obj)

    try:
        return asyncio.run(_fetch())
    except FTPClientError as e:
        console.print(f"[red]Error fetching URL: {e}[/red]")
        return b""


async def fetch_html_cached(session: aiohttp.ClientSession, url: str,
                            auth: Optional[aiohttp.BasicAuth] = None,
                            force_refresh: bool = False) -> Tuple[List[Folder], List[File]]:
    """
    Fetch and parse HTML with caching support.

    Args:
        session: aiohttp client session
        url: URL to fetch
        auth: Optional authentication
        force_refresh: If True, bypass cache

    Returns:
        Tuple of (folders, files)
    """
    cache = get_cache_manager()

    # Try cache first
    if not force_refresh:
        cached = cache.get_cached_listing(url)
        if cached:
            return cached

    # Fetch from server
    try:
        html_content = await fetch_html_with_retry(session, url, auth)
        folders, files = parse_html(url, html_content)

        # Cache the result
        cache.cache_listing(url, folders, files)

        return folders, files

    except FTPClientError:
        raise


def parse_html(base_url: str, response_html: bytes) -> Tuple[List[Folder], List[File]]:
    """Parses HTML to extract folder and file links."""
    soup = BeautifulSoup(response_html, 'html.parser')
    td_tags = soup.find_all('td', class_='fb-n')
    folders: List[Folder] = []
    files: List[File] = []

    # Add a ".." entry to go up one directory
    folders.append(Folder(name="..", url=urljoin(base_url, "..")))

    for td_tag in td_tags:
        a_tags = td_tag.find_all('a')
        for a_tag in a_tags:
            value = a_tag.text
            href = a_tag['href']

            if href.startswith('..'):
                continue  # Already handled

            absolute_url = urljoin(base_url, href)

            if href.endswith('/'):
                folders.append(Folder(name=value, url=absolute_url))
            else:
                files.append(File(name=value, url=absolute_url))

    return folders, files


async def download_file_async(session: aiohttp.ClientSession, file: File,
                              destination_dir: str = ".",
                              auth: Optional[aiohttp.BasicAuth] = None,
                              progress: Optional[Progress] = None,
                              task_id: Optional[int] = None) -> bool:
    """
    Downloads a single file to the specified directory with progress tracking (async).

    Args:
        session: aiohttp client session
        file: File to download
        destination_dir: Destination directory
        auth: Optional authentication
        progress: Optional rich progress instance
        task_id: Optional progress task ID

    Returns:
        True if successful, False otherwise
    """
    try:
        async with session.get(file.url, auth=auth) as response:
            response.raise_for_status()

            file_path = os.path.join(destination_dir, file.name)

            # Create directory if it doesn't exist
            os.makedirs(destination_dir, exist_ok=True)

            # Get file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            # Update progress task if provided
            if progress and task_id is not None:
                progress.update(task_id, total=total_size)

            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    if chunk:
                        await f.write(chunk)
                        downloaded_size += len(chunk)

                        # Update progress
                        if progress and task_id is not None:
                            progress.update(task_id, completed=downloaded_size)

            return True

    except aiohttp.ClientError as e:
        console.print(f"[red]✗ Error downloading {file.name}: {e}[/red]")
        return False
    except OSError as e:
        console.print(f"[red]✗ Error saving {file.name}: {e}[/red]")
        return False


def download_file(file: File, destination_dir: str = ".",
                 auth: Optional[Tuple[str, str]] = None) -> bool:
    """
    Synchronous wrapper for download_file_async.

    Args:
        file: File to download
        destination_dir: Destination directory
        auth: Optional tuple of (username, password)

    Returns:
        True if successful
    """
    async def _download():
        auth_obj = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with aiohttp.ClientSession() as session:
            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(f"Downloading {file.name}", total=None)
                return await download_file_async(session, file, destination_dir, auth_obj, progress, task)

    try:
        return asyncio.run(_download())
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


async def download_all_files_async(session: aiohttp.ClientSession, files: List[File],
                                  destination_dir: str = ".",
                                  auth: Optional[aiohttp.BasicAuth] = None) -> int:
    """
    Downloads all files in the list to the specified directory (async).

    Args:
        session: aiohttp client session
        files: List of files to download
        destination_dir: Destination directory
        auth: Optional authentication

    Returns:
        Number of successful downloads
    """
    if not files:
        console.print("[yellow]No files to download in this directory.[/yellow]")
        return 0

    console.print(f"\n[cyan]Starting download of {len(files)} files to '{destination_dir}'...[/cyan]\n")

    successful_downloads = 0

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        for i, file in enumerate(files, 1):
            task = progress.add_task(f"[{i}/{len(files)}] {file.name}", total=None)

            if await download_file_async(session, file, destination_dir, auth, progress, task):
                successful_downloads += 1
                progress.console.print(f"[green]✓ {file.name}[/green]")
            else:
                progress.console.print(f"[red]✗ {file.name}[/red]")

            progress.remove_task(task)

    console.print(f"\n[green]Download complete! {successful_downloads}/{len(files)} files downloaded successfully.[/green]\n")
    return successful_downloads


def download_all_files(files: List[File], destination_dir: str = ".",
                       auth: Optional[Tuple[str, str]] = None) -> None:
    """
    Synchronous wrapper for download_all_files_async.

    Args:
        files: List of files to download
        destination_dir: Destination directory
        auth: Optional tuple of (username, password)
    """
    async def _download_all():
        auth_obj = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with aiohttp.ClientSession() as session:
            return await download_all_files_async(session, files, destination_dir, auth_obj)

    try:
        asyncio.run(_download_all())
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def get_download_directory(default: Optional[str] = None) -> str:
    """
    Prompt user for download directory or use default.

    Args:
        default: Default directory (from config or current directory)

    Returns:
        Selected directory path
    """
    from rich.prompt import Prompt

    if default is None:
        default = os.getcwd()

    console.print(f"\n[bold]Download location:[/bold] [dim]{default}[/dim]")
    use_default = Prompt.ask("Use this location?", choices=["y", "n"], default="y")

    if use_default.lower() == 'y':
        return default

    custom_dir = Prompt.ask("[bold]Enter download directory[/bold]", default=default)

    # Expand user home directory
    custom_dir = os.path.expanduser(custom_dir)

    # Create if doesn't exist
    Path(custom_dir).mkdir(parents=True, exist_ok=True)

    return custom_dir
