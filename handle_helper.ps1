<#
.SYNOPSIS
    Monitors a process for open file handles related to EVE Frontier's exefile.

.DESCRIPTION
    - Monitors a process for open file handles related to EVE Frontier's exefile.
    - Also compiles and loads a mod folder defined by the $mod_folder parameter in order to inject code into the game.

.REQUIREMENTS
    - Run PowerShell as Administrator (Handle.exe requires elevated privileges)
    - EVE Frontier (https://learn.microsoft.com/sysinternals/downloads/handle)
    - Sysinternals Handle.exe (https://learn.microsoft.com/sysinternals/downloads/handle)
    - Python version 3.12 (ideally Python 3.12rc2) and python3 binary copied/renamed to python312.exe
    - 7-zip - (https://www.7-zip.org/)
    - decompiled python files / Pylingual extracts from the code.ccp file. note that the directory structure MUST be retained when editing. YMMV otherwise!

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

#>
param(
    [Parameter(Mandatory = $true)]
    [string]$ProcessName,
    [Parameter(Mandatory = $true)]
    [string]$pythonExe,
    [Parameter(Mandatory = $true)]
    [string]$HandleExe,
    [Parameter(Mandatory = $true)]
    [string]$SevenZExe,
    [Parameter(Mandatory = $true)]
    [string]$mod_folder,
    [Parameter(Mandatory = $true)]
    [string]$targetserver,
    [Parameter(Mandatory = $false)]
    [string]$recompile,
    [float]$IntervalSeconds = 0.15
)

# Path to Sysinternals Handle.exe
 # Change this to your actual path

if (-not (Test-Path $HandleExe)) {
    Write-Error "handle64.exe not found at $HandleExe"
    exit 1
}
function PythonScriptsEF {
    if ($recompile -eq $true){
        if(Test-Path $pythonExe){
            Write-Host "Recompiling mod files in $mod_folder" -ForegroundColor Green
            Get-ChildItem -Recurse $mod_folder | ForEach-Object {
                if($_.Extension -contains ".py")
                    {
                        & $pythonExe "-m" "py_compile" $_.FullName
                    }
                if ($_.FullName -match ".cpython-312.pyc")
                    {
                        $newpath = Join-Path $_.Directory ($_.Name -replace '.cpython-312.pyc', '.pyc'); 
                        if(Test-Path $newpath){
                            Write-Host "Removing leftover file from $newpath" -ForegroundColor Yellow
                            Remove-Item -Path $newpath
                            return 1
                        }
                        else{
                            Write-Host "renaming $newpath" -ForegroundColor Yellow
                            Move-Item -Path $_.FullName -Destination $newpath;
                        }

                    }
            };

        }
        else {
            Write-Host ":( Recompiling mod files in $mod_folder, but python312.exe is not available! ignoring" -ForegroundColor Red
        }
    }
    return 0
}


# Store previous handle list for comparison
$SevenZExe = Get-Item -LiteralPath $SevenZExe
$return = PythonScriptsEF
while ($return -eq 1){
    $return = PythonScriptsEF
}

Write-Host "Monitoring file handles for process: $ProcessName" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
while ($true) {
    try {
        # Run handle.exe and filter for the process
        $output = & $HandleExe -p $ProcessName 2>$null
        # Extract only file paths from output
        $currentHandles = $output |
            Select-String -Pattern "File\s+" |
            ForEach-Object { ($_ -split ":\s+", 2)[-1].Trim() } |
            Sort-Object -Unique
        if ($currentHandles -match "code.ccp"){
                $currentHandles
        }
        elseif ($currentHandles -match "manifest.dat"){
            $currentHandles
            Start-Sleep -Seconds 1
            & $pythonExe "C:\Users\sebor\OneDrive\Software\pymemstuff\lemegetonmodloader\mods\loadmod.py", $mod_folder, $targetserver, $SevenZExe

            break
        }
        # Update previous list

        Start-Sleep -Seconds $IntervalSeconds
    }
    catch {
        Write-Error "Error: $_"
        break
    }
}
#for /F "tokens=3,6 delims=: " %I IN ('C:\test\handle64.exe -accepteula "C:\CCP\EVE Frontier\utopia\code.ccp"') DO "C:\test\handle64.exe" -c %J -y -p %I