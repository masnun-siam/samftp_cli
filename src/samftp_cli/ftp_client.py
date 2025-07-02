import requests
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