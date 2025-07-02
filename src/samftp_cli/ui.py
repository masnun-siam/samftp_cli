import subprocess
from typing import List, Tuple
from pyfzf.pyfzf import FzfPrompt
from .data_models import Server, Folder, File
from .player import play_all_videos, VIDEO_EXTENSIONS, IMAGE_EXTENSIONS

def select_server(servers: List[Server]) -> Server:
    """Prompts the user to select a server."""
    print("Select a server:")
    for i, server in enumerate(servers):
        print(f"  \033[1;32;40m{i + 1}. {server.name}\033[0m")
    
    while True:
        choice = input(f"\nEnter your choice (1-{len(servers)}, q to quit): ")
        if choice.lower() == 'q':
            print("Exiting...")
            exit(0)
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(servers):
                return servers[index]
        except ValueError:
            pass
        
        print("Invalid choice. Please try again.")

def _print_menu(folders: List[Folder], files: List[File]):
    subprocess.run(['clear'])
    print("Select a value:")
    items = folders + files
    for i, item in enumerate(items):
        if isinstance(item, Folder):
            color = "\033[1;31;40m" if item.name == ".." else "\033[1;32;40m"
            print(f"{color}{i}. {item.name}\033[0m")
        else:
            if item.name.endswith(VIDEO_EXTENSIONS):
                color = "\033[1;34;40m"
            elif item.name.endswith(IMAGE_EXTENSIONS):
                color = "\033[1;33;40m"
            else:
                color = "\033[0m"
            print(f"{color}{i}. {item.name}\033[0m")


def browse_directory(folders: List[Folder], files: List[File]) -> Tuple[str, int | None]:
    """
    Displays the directory content and handles user interaction.
    Returns the action and optional selection index.
    """
    _print_menu(folders, files)
    items = folders + files
    
    choice = input(f"\nEnter your choice (0-{len(items) - 1}, s to search, p to play all, q to quit): ")
    
    if choice.lower() == 'q':
        return "quit", None
    
    if choice.lower() == 'p':
        play_all_videos(files)
        return "refresh", None

    if choice.lower() == 's':
        try:
            fzf = FzfPrompt()
            item_names = [item.name for item in items]
            selection = fzf.prompt(item_names)
            if selection:
                selected_index = item_names.index(selection[0])
                return "select", selected_index
        except FileNotFoundError:
            print("fzf command not found. Please install fzf to use search.")
        return "refresh", None

    try:
        selected_index = int(choice)
        if 0 <= selected_index < len(items):
            return "select", selected_index
    except ValueError:
        pass

    print("Invalid choice. Please try again.")
    return "refresh", None 