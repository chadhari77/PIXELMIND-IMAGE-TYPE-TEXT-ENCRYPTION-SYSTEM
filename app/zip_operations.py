import zipfile
import os

def create_zip_from_files(file_paths, output_path):
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))