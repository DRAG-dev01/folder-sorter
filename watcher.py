from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from dedupe import get_file_hash, build_hash_index
import os
import shutil
import time
import threading

DOWNLOADS_FOLDER = r"C:\Users\kiana\Downloads"


def wait_until_ready(path, checks=5, delay=0.5):
    last = -1
    stable = 0
    while stable < checks:
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            return False
        if size == last:
            stable += 1
        else:
            stable = 0
            last = size
        time.sleep(delay)
    return True

def unique_path(path):
    if not os.path.exists(path):
        return path
    name, ext = os.path.splitext(path)
    i = 1
    while True:
        p = f"{name} ({i}){ext}"
        if not os.path.exists(p):
            return p
        i += 1


FOLDER_MAP = {
    "images": [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".svg",
        ".ico",
        ".heic",
        ".heif",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dng",
        ".orf",
        ".rw2",
        ".psd",
        ".ai",
        ".eps",
        ".indd",
        ".xcf",
        ".apng",
        ".avif",
        ".jfif",
    ],
    "videos": [
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpeg",
        ".mpg",
        ".3gp",
        ".ogv",
        ".ts",
        ".mts",
        ".m2ts",
        ".vob",
        ".rm",
        ".rmvb",
        ".f4v",
        ".asf",
        ".divx",
    ],
    "audio": [
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".oga",
        ".wma",
        ".m4a",
        ".opus",
        ".aiff",
        ".aif",
        ".amr",
        ".mid",
        ".midi",
        ".caf",
        ".ac3",
        ".ape",
        ".ra",
    ],
    "documents": [
        ".pdf",
        ".doc",
        ".docx",
        ".odt",
        ".rtf",
        ".txt",
        ".tex",
        ".wpd",
        ".pages",
        ".md",
        ".rst",
        ".log",
    ],
    "spreadsheets": [".xls", ".xlsx", ".xlsm", ".xlsb", ".ods", ".csv", ".tsv"],
    "presentations": [".ppt", ".pptx", ".pps", ".ppsx", ".odp", ".key"],
    "ebooks": [".epub", ".mobi", ".azw", ".azw3", ".fb2", ".djvu", ".cbz", ".cbr"],
    "archives": [
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".lz",
        ".lzma",
        ".cab",
        ".iso",
        ".jar",
        ".war",
        ".ear",
        ".apk",
        ".ipa",
    ],
    "executables": [
        ".exe",
        ".msi",
        ".bat",
        ".cmd",
        ".com",
        ".scr",
        ".ps1",
        ".sh",
        ".bash",
        ".zsh",
        ".run",
        ".bin",
        ".app",
        ".deb",
        ".rpm",
        ".dmg",
        ".pkg",
    ],
    "programming": [
        ".py",
        ".pyw",
        ".pyc",
        ".pyo",
        ".ipynb",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".cxx",
        ".cs",
        ".vb",
        ".java",
        ".class",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".php",
        ".go",
        ".rs",
        ".swift",
        ".kt",
        ".kts",
        ".dart",
        ".lua",
        ".r",
        ".jl",
        ".pl",
        ".pm",
        ".rb",
        ".sql",
        ".xml",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
    ],
    "databases": [
        ".db",
        ".sqlite",
        ".sqlite3",
        ".mdb",
        ".accdb",
        ".dbf",
        ".sql",
        ".bak",
    ],
    "fonts": [".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon"],
    "3d_models": [
        ".obj",
        ".fbx",
        ".stl",
        ".blend",
        ".dae",
        ".3ds",
        ".gltf",
        ".glb",
        ".ply",
        ".x3d",
    ],
    "cad": [".dwg", ".dxf", ".step", ".stp", ".iges", ".igs"],
    "disk_images": [".iso", ".img", ".vhd", ".vhdx", ".vmdk", ".qcow2"],
    "certificates": [".pem", ".crt", ".cer", ".der", ".key", ".csr", ".pfx", ".p12"],
    "configuration": [
        ".env",
        ".ini",
        ".cfg",
        ".conf",
        ".yaml",
        ".yml",
        ".toml",
        ".properties",
        ".editorconfig",
    ],
    "web": [
        ".html",
        ".htm",
        ".css",
        ".js",
        ".mjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".vue",
        ".svelte",
        ".php",
        ".asp",
        ".aspx",
        ".jsp",
    ],
    "compressed_images": [".heic", ".heif", ".avif", ".webp"],
    "virtual_machines": [".ova", ".ovf", ".vdi", ".vmdk", ".vhd", ".vhdx", ".qcow2"],
    "torrent": [".torrent"],
    "email": [".eml", ".msg", ".pst", ".ost", ".mbox"],
    "misc": [
        ".tmp",
        ".old",
        ".lock",
        ".swp",
        ".part",
        ".crdownload",
        ".download",
        ".dat",
        ".cache",
    ],
}

# Build extension -> folder lookup dictionary
EXTENSION_MAP = {}

for folder, extensions in FOLDER_MAP.items():
    for ext in extensions:
        EXTENSION_MAP[ext.lower()] = folder


class MyHandler(FileSystemEventHandler):

    def __init__(self):
        self.recently_moved = set()
        self.seen_hashes = build_hash_index(DOWNLOADS_FOLDER)

    def on_created(self, event):
        print("EVENT FIRED:", event.src_path)
        if event.is_directory:
            return

        path = event.src_path

        if os.path.dirname(path) != DOWNLOADS_FOLDER:
            return

        if not wait_until_ready(path):
            return

        if path in self.recently_moved:
            return

        _, extension = os.path.splitext(path)
        extension = extension.lower()

        for _ in range(10):
            try:
                file_hash = get_file_hash(path)
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.5)
        else:
            return

        existing = self.seen_hashes.get(file_hash)

        if existing and os.path.exists(existing):
            duplicates_folder = os.path.join(DOWNLOADS_FOLDER, "Duplicates")
            os.makedirs(duplicates_folder, exist_ok=True)
            destination_path = os.path.join(duplicates_folder, os.path.basename(path))
            print(f"Duplicate found: {os.path.basename(path)} matches {existing}")
        else:
            folder = EXTENSION_MAP.get(extension, "misc")
            destination_folder = os.path.join(DOWNLOADS_FOLDER, folder)
            os.makedirs(destination_folder, exist_ok=True)
            destination_path = os.path.join(destination_folder, os.path.basename(path))
            destination_path = unique_path(destination_path)

            self.seen_hashes[file_hash] = destination_path

        if os.path.abspath(path) == os.path.abspath(destination_path):
            return

        for _ in range(10):
            try:
                shutil.move(path, destination_path)
                self.recently_moved.add(destination_path)
                threading.Timer(
                    2,
                    lambda: self.recently_moved.discard(destination_path)
                ).start()
                print(f"Moved: {os.path.basename(path)} -> {os.path.basename(os.path.dirname(destination_path))}")
                break
            except (PermissionError, FileNotFoundError):
                time.sleep(0.5)
            except Exception as e:
                print(f"Error moving {path}: {e}")
                break


if __name__ == "__main__":
    observer = Observer()
    observer.schedule(MyHandler(), DOWNLOADS_FOLDER, recursive=True)
    observer.start()

    print(f"Watching: {DOWNLOADS_FOLDER}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
