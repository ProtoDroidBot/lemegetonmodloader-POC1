import subprocess
import psutil
import sys
import subprocess
import shutil
from pathlib import Path
import zipfile
import os
mod_folder = sys.argv[1]
targetserver = sys.argv[2]
SevenZExe = sys.argv[3]
def get_pid_by_name(process_name):
    """Return the PID of the first process matching the given name."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None

def load_mods_into_path_modules(target_path, mod_dir, file):
    import_target_input = str(f"{target_path}")
    replace_target=(target_path.replace("\\__pycache__", "")).replace(f"{mod_dir}\\", '')
    print(replace_target)
    try:
        # Copy the file to the destination directory

        mod_zip = str(mod_dir + "\\code.ccp")
        remove_file_from_7zip(mod_zip, replace_target, file)
        # Insert the file into the existing ZIP archive using append mode ('a')
        with zipfile.ZipFile(mod_zip, 'a', compression=zipfile.ZIP_STORED) as zipf:

            zipf.write(import_target_input, arcname=str(replace_target.replace(mod_dir, '') + "/"))
            print(f"Added {import_target_input} to {mod_zip}")

    except Exception as e:
        print(f"An unexpected error occurred in load_mods_into_path_modules: {e}")

def remove_file_from_7zip(archive_path, file_to_remove, file):
    #seven_zip_executable = 'C:\\Program Files\\7-Zip\\7z.exe' 
    seven_zip_executable = Path(f'{SevenZExe}')
    print("Attempting file removal")
    # The command is '7z d archive.zip file_to_delete'
    command = [
        seven_zip_executable,
        'd',          # 'd' stands for delete
        '-y',
        archive_path,
        file_to_remove
    ]
    try:
        # Run the command
        subprocess.run(command, check=True, text=True, stdin=subprocess.DEVNULL )
        print(f"Successfully removed '{file_to_remove}' from '{archive_path}'")

    except subprocess.CalledProcessError as e:
        print(f"Error removing file: {e.stderr}")
    except FileNotFoundError:
        print(f"Error: The 7-Zip 7z executable '{seven_zip_executable}' was not found.")
        print("Please check your installation and ensure the executable is in your PATH or provide its full path.")

try:
    shutil.copy(Path(f'C:\\CCP\\EVE Frontier\\{targetserver}\\code.ccp'), mod_folder)
    mod_dir_abs = str(f'{mod_folder}')
    compiled_directory_path = Path(f'{mod_dir_abs}')
    for root, dirs, files in os.walk(compiled_directory_path):
        for file in files:
            if file == "code.ccp":
                continue
            elif file.endswith(".pyc"):
                full_file_path = os.path.join(root, file)
                load_mods_into_path_modules(full_file_path, mod_dir_abs, file)
            else:
                continue
    shutil.copy(Path(f"{mod_folder}\\code.ccp"), f'C:\\CCP\\EVE Frontier\\{targetserver}\\code.ccp')
    print("Success! Press any key to exit\n")
    exit()
except Exception as e:
    print(f"Failed to load mods due to {e}. :( \n")
    exit()

else:
    exit()
        