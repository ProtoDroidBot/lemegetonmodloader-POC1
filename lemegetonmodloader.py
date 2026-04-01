
import psutil
import time
from mods import loadmod
import os
import subprocess
import asyncio
from pathlib import Path

async def gamelauncher(work, commandline):
    try:
        await asyncio.sleep(2)
        subprocess.run([work, commandline[2], commandline[3], commandline[4], commandline[5], commandline[6], commandline[7], commandline[8], commandline[9], commandline[10]])


    except Exception as e:
        print(f"Game Subprocess error:  ", e)

#def main(work, commandline):
    #print(os.getcwd())
    #await asyncio.gather(compiler(work, os.getcwd()), gamelauncher(work, commandline))

async def main():
    while True:
        time.sleep(2)
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        # The cmdline() method returns a list of the command line arguments
        # You can filter based on process name or other criteria
            if 'exefile' in process.name() and process.cmdline():
                print(f"PID: {process.info['pid']}, Name: {process.info['name']}")
                print(f"Command line: {process.cmdline()}")
                command = process.cmdline()
                print(f"Game EXE: {process.exe()}")
                game_exe = process.exe()
                process.kill()

                results = asyncio.gather(
                    gamelauncher(game_exe, command),
                    loadmod.modloader(Path(game_exe), os.getcwd())
                )
                print(f"finished at {time.strftime('%X')}")
                print(f"Results: {results}")
                break

if __name__ == "__main__":
    print(f"Awaiting EVE Frontier exefile.exe execution. Please launch the game via the EVE Frontier Launcher.")
    asyncio.run(main())