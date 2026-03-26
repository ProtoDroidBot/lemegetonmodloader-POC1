[Test Mod Loader for EVE Frontier]

<#
.SYNOPSIS
    Monitors target process for open file handles related to EVE Frontier's exefile.
    Attempts to patch code.ccp with modified files from the mod folder during a very specific/tight window.

.AUTHOR Author of this toolkit and script
    ProtoDroidBot (EVE Frontier and GitHub name)

.DESCRIPTION
    - Monitors a process for open file handles related to EVE Frontier's exefile.
    - Also compiles and loads a mod folder defined by the $mod_folder parameter in order to inject code into the game.

.REQUIREMENTS Requirements for using this script
    - Run PowerShell as Administrator (Handle.exe requires elevated privileges)
    - EVE Frontier (https://www.evefrontier.com/)
    - Sysinternals Handle.exe (https://learn.microsoft.com/sysinternals/downloads/handle)
    - Python version 3.12 (ideally Python 3.12rc2) and python3 binary copied/renamed to python312.exe
    - 7-zip - (https://www.7-zip.org/)
    - decompiled python files / Pylingual extracts from the code.ccp file. note that the directory structure MUST be retained when editing. YMMV otherwise!
    ! - Note that I shouldn't provide the decompiled python files from the code.ccp file due to legal reasons, but you can obtain them yourself using a tool like Pylingual
    ! - Some editing required on the decompiled python files is needed in order to get them to compile because of the way Python 3.12 bytecode works.

.PARAMETER ProcessName
    $ProcessName should be set to the exefile.exe of EVE Frontier

.PARAMETER pythonExe
    $pythonExe is the path to the python executable (ideally python 3.12rc2) that will be used to compile the mod files and run the loadmod.py script.

.PARAMETER HandleExe
    $HandleExe is the path to the Sysinternals Handle.exe utility.

.PARAMETER SevenZExe
    $SevenZExe is the path to the 7-zip executable, used for extracting and repacking the code.ccp file.

.PARAMETER mod_folder
    $mod_folder is the path to the folder containing the mod files. This folder will be monitored for .py files to compile and load into the game.

.PARAMETER targetserver
    $targetserver is the server folder name of the EVE Frontier installation, used for targeting the correct code.ccp file for modding.

.PARAMETER recompile
    $recompile is a boolean flag that determines whether the mod files should be recompiled on each run. Set to $true to enable recompilation, or $false to skip it.
.PARAMETER precached
    $precached is a boolean flag that determines whether the mod files should be precached on each run. Set to $true to enable precaching, or $false to skip it.
.PARAMETER interval
    $Interval is a int value that determines the sleep interval (in seconds) between checks for the process and file handles. Default is 1.5 seconds. Adjust this number as needed.
#>




Example Command line: Requires PowerShell 7
Set-ExecutionPolicy Bypass; pwsh .\handle_helper.ps1 -ProcessName exefile.exe -pythonExe C:\Users\sebor\AppData\Local\Programs\Python\Python312\python.exe -HandleExe .\handle.exe -SevenZExe "C:\Program Files\7-Zip\7z.exe" -mod_folder C:\Users\sebor\OneDrive\Software\GitHub\lemegetonmodloader-POC1\mods\SSU_to_Industry -targetserver utopia -recompile $true -Interval 1.5 -precached false

Previous Command lines:
Very old and was pre-PowerShell 7 (PowerShell 5) and this did NOT support parallel ForEach-Object command execution that I needed
```Set-ExecutionPolicy Bypass; .\handle_helper.ps1 -ProcessName exefile.exe -pythonExe C:\Users\username\AppData\Local\Programs\Python\Python312\python.exe -HandleExe .\handle.exe -SevenZExe "C:\Program Files\7-Zip\7z.exe" -mod_folder C:\Users\username\OneDrive\Software\pymemstuff\lemegetonmodloader\mods\SSU_to_Industry -targetserver utopia -recompile $true```

Requires PowerShell 7
```Set-ExecutionPolicy Bypass; pwsh .\handle_helper.ps1 -ProcessName exefile.exe -pythonExe C:\Users\sebor\AppData\Local\Programs\Python\Python312\python.exe -HandleExe .\handle.exe -SevenZExe "C:\Program Files\7-Zip\7z.exe" -mod_folder C:\Users\sebor\OneDrive\Software\GitHub\lemegetonmodloader-POC1\mods\SSU_to_Industry -targetserver utopia -recompile $true -Interval 0.7 -precached false```
