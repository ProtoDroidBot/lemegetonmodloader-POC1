import subprocess
import psutil
import time
import asyncio
import subprocess
import shutil
from pathlib import Path
import zipfile
import os

def get_pid_by_name(process_name):
    """Return the PID of the first process matching the given name."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return proc.info['pid']
    return None


def load_mods_into_path_modules(target_path, mod_dir):
    import_target_input = str(f"{target_path}")
    replace_target=(target_path.replace("\\__pycache__", "")).replace(f"{mod_dir}\\", '')
    print(replace_target)
    try:
        # Copy the file to the destination directory

        #mod_zip = Path.joinpath(mod_dir, "code.ccp")
        remove_file_from_7zip(mod_dir, replace_target)
        # Insert the file into the existing ZIP archive using append mode ('a')
        with zipfile.ZipFile(mod_dir, 'a', compression=zipfile.ZIP_STORED) as zipf:

            zipf.write(import_target_input, arcname=str(replace_target.replace(mod_dir, '') + "/"))
            print(f"Added {import_target_input} to {mod_dir}")

    except Exception as e:
        print(f"An unexpected error occurred in load_mods_into_path_modules: {e}; please inform ProtoDroidBot and create an issue on GitHub at: ")

def remove_file_from_7zip(archive_path, file_to_remove):
    #seven_zip_executable = 'C:\\Program Files\\7-Zip\\7z.exe' 
    seven_zip_executable = Path(os.getcwd(), '7za.exe')
    print(f"Attempting file replace/removal with 7za.exe from: {seven_zip_executable}")
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
        print(f"Error removing file from the modded code.ccp file: {e}")
    except Exception as err:
        print(f"There was another unresolved error in the remove_file_from_7zip function: {err}; please inform ProtoDroidBot and create an issue on GitHub at: ")

async def modloader(gamepath, mod_folder):
    try:
        game_dir = Path(gamepath)
        #print(game_dir.parent.parent)
        mod_dir = Path(mod_folder, 'mods')
        print(mod_folder, mod_dir)
        codeccp = mod_dir.joinpath(mod_dir, 'code.ccp')
        #game_dir = game_dir[:-2].with_segments()
        #{gamepath}\\{targetserver}\\code.ccp
        game_dir2 = Path.joinpath(game_dir.parent.parent, 'code.ccp')
        #print(game_dir2)
        shutil.copy(Path(game_dir2), mod_dir)
        #mod_dir_abs = str(f'{mod_folder}')
        #compiled_directory_path = Path(f'{mod_dir_abs}')

        #for root, dirs, files in os.walk(mod_dir):
            #for file in files:
                #if file == "code.ccp":
                    #continue
                #elif file.endswith(".pyc"):
                    #full_file_path = os.path.join(root, file)
                    #load_mods_into_path_modules(full_file_path, codeccp)
                #else:
                    #continue
                #Path(f"{mod_folder}\\code.ccp")
        time.sleep(6.5)
        shutil.copy(codeccp, game_dir2)
        print("Code.ccp file overwritten, game should launch with the modified file\n")
    except Exception as e:
        print(f"Failed to load mods due to this error: {e}. :( \n")
        