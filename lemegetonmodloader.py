import asyncio
import psutil
import time
from mods import loadmod
import os

async def compiler(work, modfolder):
    print("Compiler running")
    loadmod.modloader(work, modfolder)

async def gamelauncher(commandline):
    asyncio.sleep(2.5)
    print("Game launch routines running")

async def main(work, commandline):
    print(os.getcwd())
    await asyncio.gather(compiler(work, os.getcwd()), gamelauncher(commandline))

if __name__ == "__main__":
    while True:
        time.sleep(1)
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        # The cmdline() method returns a list of the command line arguments
        # You can filter based on process name or other criteria
            if 'exefile' in process.name() and process.cmdline():
                print(f"PID: {process.info['pid']}, Name: {process.info['name']}")
                print(f"Command line: {process.info['cmdline'][1]}")
                command = process.info['cmdline']
                asyncio.run(main(command[1], command))
                time.sleep(10)
                break