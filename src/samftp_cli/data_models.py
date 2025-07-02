from dataclasses import dataclass

@dataclass
class Server:
    name: str
    url: str

@dataclass
class File:
    name: str
    url: str

@dataclass
class Folder:
    name: str
    url: str 