import hashlib
import os


def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_hash_index(base_folder):
    seen_hashes = {}
    for root, dirs, files in os.walk(base_folder):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                seen_hashes[get_file_hash(filepath)] = filepath
            except (PermissionError, FileNotFoundError):
                continue
    return seen_hashes
