import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from .data_models import Server

def get_config_path() -> Path:
    """Returns the path to the configuration file in the user's home directory."""
    return Path.home() / ".samftp-cli.env"

def load_servers_from_env() -> List[Server]:
    """
    Loads server configurations from the config file (~/.samftp-cli.env).
    """
    config_path = get_config_path()
    if config_path.exists():
        load_dotenv(dotenv_path=config_path)
    
    servers: List[Server] = []
    i = 1
    while True:
        name = os.getenv(f"SERVER_{i}_NAME")
        url = os.getenv(f"SERVER_{i}_URL")

        if not all([name, url]):
            break

        servers.append(Server(name=name, url=url))
        i += 1
    
    if not servers:
        print("Warning: No server configurations found.")
        print(f"Please create a configuration file at: {config_path}")
        print("You can copy the contents from .env.example to get started.")

    return servers 