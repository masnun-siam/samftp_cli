import os
from .config import load_servers_from_env
from .ftp_client import fetch_html, parse_html, download_all_files
from .ui import select_server, browse_directory
from .player import play_file
from .data_models import Folder, File

def main():
    """Main function for the SAM-FTP CLI application."""
    servers = load_servers_from_env()
    if not servers:
        return

    selected_server = select_server(servers)
    current_url = selected_server.url

    while True:
        html_content = fetch_html(current_url)
        if not html_content:
            print(f"Could not fetch content from {current_url}")
            break

        folders, files = parse_html(current_url, html_content)

        action, selected_index = browse_directory(folders, files)

        if action == "quit":
            break
        
        if action == "refresh":
            continue

        if action == "download":
            download_all_files(files, os.getcwd())
            continue

        if action == "select" and selected_index is not None:
            items = folders + files
            selected_item = items[selected_index]

            if isinstance(selected_item, Folder):
                current_url = selected_item.url
            elif isinstance(selected_item, File):
                play_file(selected_item)

if __name__ == "__main__":
    main() 