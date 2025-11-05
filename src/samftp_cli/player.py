import subprocess
import tempfile
import shutil
from typing import List, Optional
from rich.console import Console
from rich.prompt import Prompt
from .data_models import File

console = Console()

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp')
AUDIO_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.wav', '.ogg', '.aac')

# Session-level player cache
_session_player = None


def get_available_players() -> List[str]:
    """Returns a list of available media players on the system."""
    players = ['mpv', 'vlc', 'iina']
    available = []
    for player in players:
        if shutil.which(player):
            available.append(player)
    return available


def get_player_preference(force_prompt: bool = False, override: Optional[str] = None) -> Optional[str]:
    """
    Get player preference with multiple fallback options.

    Priority:
    1. Override parameter (from --player flag)
    2. Session-level cache (already selected this session)
    3. Saved preference in config
    4. Prompt user

    Args:
        force_prompt: Force user to select player even if preference exists
        override: Override player selection

    Returns:
        Selected player name or None
    """
    global _session_player

    # Priority 1: Override
    if override:
        available_players = get_available_players()
        if override in available_players:
            _session_player = override
            return override
        else:
            console.print(f"[yellow]Warning: Player '{override}' not available, falling back to preference[/yellow]")

    # Priority 2: Session cache
    if not force_prompt and _session_player:
        return _session_player

    # Priority 3: Saved preference
    if not force_prompt:
        from .config import get_default_player
        saved_player = get_default_player()
        if saved_player:
            available_players = get_available_players()
            if saved_player in available_players:
                _session_player = saved_player
                return saved_player
            else:
                console.print(f"[yellow]Saved player '{saved_player}' not available, please select another[/yellow]")

    # Priority 4: Prompt user
    return select_media_player()


def select_media_player(save_preference: bool = True) -> Optional[str]:
    """
    Prompts the user to select a media player.

    Args:
        save_preference: If True, save selection to config

    Returns:
        Selected player name or None
    """
    global _session_player

    available_players = get_available_players()

    if not available_players:
        console.print("[red]Error: No supported media players found.[/red]")
        console.print("[dim]Please install mpv, VLC, or IINA.[/dim]")
        return None

    if len(available_players) == 1:
        console.print(f"[cyan]Using {available_players[0]} (only available player)[/cyan]")
        _session_player = available_players[0]
        return available_players[0]

    console.print("\n[bold]Select a media player:[/bold]")
    for i, player in enumerate(available_players):
        console.print(f"  [cyan]{i + 1}. {player}[/cyan]")

    while True:
        try:
            choice = Prompt.ask(f"\n[bold]Enter your choice[/bold] (1-{len(available_players)})")
            index = int(choice) - 1
            if 0 <= index < len(available_players):
                selected = available_players[index]
                _session_player = selected

                if save_preference:
                    from .config import set_default_player
                    should_save = Prompt.ask(
                        f"[bold]Save {selected} as default player?[/bold]",
                        choices=["y", "n"],
                        default="y"
                    )
                    if should_save.lower() == 'y':
                        if set_default_player(selected):
                            console.print(f"[green]✓ Saved {selected} as default player[/green]")

                return selected
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")
        except (ValueError, KeyboardInterrupt):
            console.print("[red]Invalid choice. Please try again.[/red]")


def change_player():
    """Allow user to change player mid-session."""
    global _session_player
    console.print("\n[bold cyan]Change Media Player[/bold cyan]")
    _session_player = None  # Clear session cache
    return select_media_player(save_preference=True)


def play_file_with_mpv(file: File, background: bool = True):
    """
    Plays a single media file using mpv.

    Args:
        file: File to play
        background: If True, play in background (non-blocking)
    """
    if file.url.endswith(IMAGE_EXTENSIONS):
        subprocess.Popen(
            ["mpv", "--loop-file=inf", file.url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    elif file.url.endswith(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS):
        if background:
            subprocess.Popen(
                ['mpv', file.url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.run(['mpv', file.url])


def play_file_with_vlc(file: File, background: bool = True):
    """
    Plays a single media file using VLC.

    Args:
        file: File to play
        background: If True, play in background (non-blocking)
    """
    if background:
        subprocess.Popen(
            ["vlc", file.url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.run(['vlc', file.url])


def play_file_with_iina(file: File, background: bool = True):
    """
    Plays a single media file using IINA.

    Args:
        file: File to play
        background: If True, play in background (non-blocking)
    """
    if background:
        subprocess.Popen(
            ["iina", file.url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.run(['iina', file.url])


def play_file(file: File, player: Optional[str] = None, background: bool = True):
    """
    Plays a single media file using the selected media player.

    Args:
        file: File to play
        player: Optional player override
        background: If True, play in background (non-blocking)
    """
    selected_player = player or get_player_preference()
    if not selected_player:
        return

    console.print(f"[cyan]▶ Playing[/cyan] [bold]{file.name}[/bold] [dim]with {selected_player}[/dim]")

    if selected_player == 'mpv':
        play_file_with_mpv(file, background)
    elif selected_player == 'vlc':
        play_file_with_vlc(file, background)
    elif selected_player == 'iina':
        play_file_with_iina(file, background)

    if background:
        console.print("[dim]Playing in background, you can continue browsing...[/dim]")


def play_all_videos_with_mpv(files: List[File], background: bool = True):
    """
    Creates a temporary playlist file and plays all videos in mpv.

    Args:
        files: List of files to play
        background: If True, play in background (non-blocking)
    """
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS)]
    if not video_files:
        console.print("[yellow]No media files to play.[/yellow]")
        return

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".m3u") as playlist:
        playlist.write('\n'.join(video_files))
        playlist_name = playlist.name

    console.print(f"[cyan]▶ Playing {len(video_files)} files with mpv...[/cyan]")

    if background:
        subprocess.Popen(
            ['mpv', f'--playlist={playlist_name}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        console.print("[dim]Playing in background, you can continue browsing...[/dim]")
    else:
        subprocess.run(['mpv', f'--playlist={playlist_name}'])


def play_all_videos_with_vlc(files: List[File], background: bool = True):
    """
    Plays all videos in VLC by passing multiple URLs as arguments.

    Args:
        files: List of files to play
        background: If True, play in background (non-blocking)
    """
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS)]
    if not video_files:
        console.print("[yellow]No media files to play.[/yellow]")
        return

    console.print(f"[cyan]▶ Playing {len(video_files)} files with VLC...[/cyan]")

    if background:
        subprocess.Popen(
            ['vlc'] + video_files,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        console.print("[dim]Playing in background, you can continue browsing...[/dim]")
    else:
        subprocess.run(['vlc'] + video_files)


def play_all_videos_with_iina(files: List[File], background: bool = True):
    """
    Plays all videos in IINA by passing multiple URLs as arguments.

    Args:
        files: List of files to play
        background: If True, play in background (non-blocking)
    """
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS + AUDIO_EXTENSIONS)]
    if not video_files:
        console.print("[yellow]No media files to play.[/yellow]")
        return

    console.print(f"[cyan]▶ Playing {len(video_files)} files with IINA...[/cyan]")

    if background:
        subprocess.Popen(
            ['iina'] + video_files,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        console.print("[dim]Playing in background, you can continue browsing...[/dim]")
    else:
        subprocess.run(['iina'] + video_files)


def play_all_videos(files: List[File], player: Optional[str] = None, background: bool = True):
    """
    Creates a playlist and plays all videos using the selected media player.

    Args:
        files: List of files to play
        player: Optional player override
        background: If True, play in background (non-blocking)
    """
    selected_player = player or get_player_preference()
    if not selected_player:
        return

    if selected_player == 'mpv':
        play_all_videos_with_mpv(files, background)
    elif selected_player == 'vlc':
        play_all_videos_with_vlc(files, background)
    elif selected_player == 'iina':
        play_all_videos_with_iina(files, background)


def is_media_file(filename: str) -> bool:
    """Check if filename is a supported media file."""
    return filename.lower().endswith(VIDEO_EXTENSIONS + IMAGE_EXTENSIONS + AUDIO_EXTENSIONS)


def get_file_type(filename: str) -> Optional[str]:
    """Get file type (video, audio, image) from filename."""
    filename_lower = filename.lower()
    if filename_lower.endswith(VIDEO_EXTENSIONS):
        return "video"
    elif filename_lower.endswith(AUDIO_EXTENSIONS):
        return "audio"
    elif filename_lower.endswith(IMAGE_EXTENSIONS):
        return "image"
    return None
