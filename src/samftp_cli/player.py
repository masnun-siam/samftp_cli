import subprocess
import tempfile
import shutil
from typing import List, Optional
from .data_models import File

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')

def get_available_players() -> List[str]:
    """Returns a list of available media players on the system."""
    players = ['mpv', 'vlc', 'iina']
    available = []
    for player in players:
        if shutil.which(player):
            available.append(player)
    return available

def select_media_player() -> Optional[str]:
    """Prompts the user to select a media player."""
    available_players = get_available_players()
    
    if not available_players:
        print("Error: No supported media players found. Please install mpv, VLC, or IINA.")
        return None
    
    if len(available_players) == 1:
        print(f"Using {available_players[0]} (only available player)")
        return available_players[0]
    
    print("Select a media player:")
    for i, player in enumerate(available_players):
        print(f"  {i + 1}. {player}")
    
    while True:
        try:
            choice = input(f"\nEnter your choice (1-{len(available_players)}): ")
            index = int(choice) - 1
            if 0 <= index < len(available_players):
                return available_players[index]
            else:
                print("Invalid choice. Please try again.")
        except (ValueError, KeyboardInterrupt):
            print("Invalid choice. Please try again.")

def play_file_with_mpv(file: File):
    """Plays a single media file using mpv."""
    if file.url.endswith(IMAGE_EXTENSIONS):
        subprocess.Popen(["mpv", "--loop-file=inf", file.url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif file.url.endswith(VIDEO_EXTENSIONS):
        subprocess.run(['mpv', file.url])

def play_file_with_vlc(file: File):
    """Plays a single media file using VLC."""
    if file.url.endswith(IMAGE_EXTENSIONS):
        # VLC can display images but doesn't have a loop option like mpv
        subprocess.Popen(["vlc", file.url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif file.url.endswith(VIDEO_EXTENSIONS):
        subprocess.run(['vlc', file.url])

def play_file_with_iina(file: File):
    """Plays a single media file using IINA."""
    if file.url.endswith(IMAGE_EXTENSIONS):
        subprocess.Popen(["iina", file.url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif file.url.endswith(VIDEO_EXTENSIONS):
        subprocess.run(['iina', file.url])

def play_file(file: File):
    """Plays a single media file using the selected media player."""
    player = select_media_player()
    if not player:
        return
    
    print(f"Playing {file.name} with {player}...")
    
    if player == 'mpv':
        play_file_with_mpv(file)
    elif player == 'vlc':
        play_file_with_vlc(file)
    elif player == 'iina':
        play_file_with_iina(file)

def play_all_videos_with_mpv(files: List[File]):
    """Creates a temporary playlist file and plays all videos in mpv."""
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS)]
    if not video_files:
        print("No video files to play.")
        return

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".m3u") as playlist:
        playlist.write('\n'.join(video_files))
        playlist_name = playlist.name

    print(f"Playing {len(video_files)} videos with mpv...")
    try:
        subprocess.run(['mpv', f'--playlist={playlist_name}'])
    finally:
        # The playlist file is left in temp for inspection, OS will clean it up
        pass

def play_all_videos_with_vlc(files: List[File]):
    """Plays all videos in VLC by passing multiple URLs as arguments."""
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS)]
    if not video_files:
        print("No video files to play.")
        return

    print(f"Playing {len(video_files)} videos with VLC...")
    subprocess.run(['vlc'] + video_files)

def play_all_videos_with_iina(files: List[File]):
    """Plays all videos in IINA by passing multiple URLs as arguments."""
    video_files = [f.url for f in files if f.url.endswith(VIDEO_EXTENSIONS)]
    if not video_files:
        print("No video files to play.")
        return

    print(f"Playing {len(video_files)} videos with IINA...")
    subprocess.run(['iina'] + video_files)

def play_all_videos(files: List[File]):
    """Creates a playlist and plays all videos using the selected media player."""
    player = select_media_player()
    if not player:
        return
    
    if player == 'mpv':
        play_all_videos_with_mpv(files)
    elif player == 'vlc':
        play_all_videos_with_vlc(files)
    elif player == 'iina':
        play_all_videos_with_iina(files) 