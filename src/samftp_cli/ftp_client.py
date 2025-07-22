import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Tuple
from .data_models import Folder, File

def fetch_html(url: str) -> bytes:
    """Fetches HTML content from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return b""


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
                continue # Already handled

            absolute_url = urljoin(base_url, href)

            if href.endswith('/'):
                folders.append(Folder(name=value, url=absolute_url))
            else:
                files.append(File(name=value, url=absolute_url))

    return folders, files


def download_file(file: File, destination_dir: str = ".") -> bool:
    """Downloads a single file to the specified directory."""
    try:
        response = requests.get(file.url, stream=True)
        response.raise_for_status()
        
        file_path = os.path.join(destination_dir, file.name)
        
        # Create directory if it doesn't exist
        os.makedirs(destination_dir, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Downloaded: {file.name}")
        return True
        
    except requests.RequestException as e:
        print(f"Error downloading {file.name}: {e}")
        return False
    except OSError as e:
        print(f"Error saving {file.name}: {e}")
        return False


def download_all_files(files: List[File], destination_dir: str = ".") -> None:
    """Downloads all files in the list to the specified directory."""
    if not files:
        print("No files to download in this directory.")
        return
    
    print(f"Starting download of {len(files)} files to '{destination_dir}'...")
    
    successful_downloads = 0
    total_files = len(files)
    
    for i, file in enumerate(files, 1):
        print(f"[{i}/{total_files}] Downloading {file.name}...")
        if download_file(file, destination_dir):
            successful_downloads += 1
    
    print(f"\nDownload complete! {successful_downloads}/{total_files} files downloaded successfully.") 