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
    [Parameter(Mandatory = $true)]
    [string]$precached,
    [float]$Interval = 1.5
)

# Path to Sysinternals Handle.exe

if (-not (Test-Path $HandleExe)) {
    Write-Error "handle64.exe not found at $HandleExe"
    exit 1
}

# Python 3.12 script compiler and code.ccp packing
# Sometimes this process errors out because of file locks on the code.ccp file
# If this happens, just run the script again after deleting the code.ccp.tmp file and it should work on the next try. 

function PythonScriptsEF {
    if ($recompile -eq $true){
        if(Test-Path $pythonExe){
            Write-Host "Recompiling mod files in $mod_folder" -ForegroundColor Green
            Get-ChildItem -Recurse $mod_folder | ForEach-Object {
                if($_.Extension -contains ".py")
                    {
                        & $pythonExe "-m" "py_compile" $_.FullName
                    }
                }
            Write-Host "cleaning up $mod_folder and moving stuff to the proper place" -ForegroundColor Green
            Get-ChildItem -Recurse $mod_folder | ForEach-Object {
                if ($_.FullName -match ".cpython-312.pyc")
                    {
                        $newpath = Join-Path $_.Directory ($_.Name -replace '.cpython-312.pyc', '.pyc'); 
                        if(Test-Path $newpath){
                            Write-Host "Removing leftover file from $newpath" -ForegroundColor Yellow
                            Remove-Item -Path $newpath
                            Write-Host "renaming $newpath" -ForegroundColor Yellow
                            Move-Item -Path $_.FullName -Destination $newpath;
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
            return 1
        }
    }
    return 0
}

# Function to monitor file handles for the specified process, then attempts to inject mod files once the target file handle is detected and released by the game.
# Do note that the injection method used here is very rudimentary and may not work in all cases.
# It relies on the game releasing the manifest.dat file handle after loading it, which may not always happen in a predictable manner.
# Also this script requires PowerShell 7 because of the use of Foreach-Object -Parallel, which is used to attempt to time the injection of the mod files during the window of time where the game has released the manifest.dat file handle checking on code.ccp but exefile.exe (Game process) has not yet reloaded it.
function HandleHelper(){
    Write-Host "Monitoring file handles for process: $ProcessName" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
    while ($true) {
        try{
            # Get the process ID of the target process using WMI.
            $test = Get-WmiObject Win32_Process -Filter "Name = 'exefile.exe'" | Select-Object Name, ProcessId, CommandLine
            $pids = $test.ProcessId

            # PowerShell stopwatch object to time the file handle release.
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            if ($test -ne $null) {
                Write-Host "caught process" -ForegroundColor Yellow
                # Run handle.exe and filter for the process
                $sw.restart()
                $output = & $HandleExe -acceptEula -p $ProcessName 2>$null
                # Extract only file paths from output
                $currentHandles = $output |
                    Select-String -Pattern "File\s+" |
                    ForEach-Object { ($_ -split ":\s+", 2)[-1].Trim() } |
                    Sort-Object -Unique
                $currentHandles
                if ($currentHandles -match "manifest.dat"){
                    # After grabbing the time elapsed, we can then reuse this time value to attempt to time the injection of the mod files 
                    $sw.Stop()
                    Write-Output "Total time elapsed: $($sw.Elapsed.TotalSeconds) seconds"

                    # This bit grabs the command line from $test and subsstring splits it into variables to be used for starting the game process again after killing it to attempt to force the game to reload the code.ccp file.
                    # to inject the mod files during the window of time where the manifest.dat file handle is released but the game process is still running, which should cause the game to load the modded code.ccp file instead of the original one.
                    # Also makes it so that you dont have to start the game through the command line every time, which is a QoL improvement for testing mod files.
                    # Also starts the game without /noconsole for debugging purposes.
                    Write-Host "attempting to grab command line argumentsto pipe back into a separate process" -ForegroundColor Yellow
                    $exe, $b, $c, $d, $e, $f, $g, $h, $i, $j = ($test.CommandLine).Split("/", 10)
                    $c = $c.Substring(0, 0) + "/"+ $c.Substring(0).Replace('"', "")
                    $d = $d.Substring(0, 0) + "/"+ $d.Substring(0).Replace('"', "")
                    $e = $e.Substring(0, 0) + "/"+ $e.Substring(0).Replace('"', "")
                    $f = $f.Substring(0, 0) + "/"+ $f.Substring(0).Replace('"', "")
                    $g = $g.Substring(0, 0) + "/"+ $g.Substring(0).Replace('"', "")
                    $h = $h.Substring(0, 0) + "/"+ $h.Substring(0).Replace('"', "")
                    $i = $i.Substring(0, 0) + "/"+ $i.Substring(0).Replace('"', "")
                    $j = $j.Substring(0, 0) + "/"+ $j.Substring(0).Replace('"', "")
                    $exe = $exe.Replace('"', "")
                    Stop-Process -Id $pids -Force

                    Write-Host "Attempting to inject mod files..." -ForegroundColor Yellow
                    
                    # This bit of scriptblock required me to use PowerShell 7 because of -Parallel, which is used here to time the injection of the mod files with the compilation of the code.ccp file.
                    # Idea is to compile the mod file and patch the code.ccp file in the specified time window where the manifest.dat file handle is released and the game process hasn't loaded code.ccp yet.
                    # This is the meat of the exploit.
                    # If the timing is off even slightly, it will either cause invalid file header errors in code.ccp, import errors, or best case the game complains about modified files.
                    1..2 | Foreach-Object -Parallel {
                        if ($_ -eq 1){
                            ($using:sw.Elapsed.TotalSeconds)
                            $using:Interval
                            Start-Sleep -Seconds ($using:sw.Elapsed.TotalSeconds)
                            & $using:pythonExe .\mods\loadmod.py $using:mod_folder $using:targetserver $using:SevenZExe $using:precached

                        }else{
                            Start-Sleep -Seconds ($using:Interval + $using:sw.Elapsed.TotalSeconds)
                            Start-Process -FilePath $using:exe -ArgumentList "$using:c, $using:d, $using:e, $using:f, $using:g, $using:h, $using:i, $using:j"
                        }

                    }
                    break
                }

            }

    } catch {
            Write-Error "Error: $_"
            break
        }
    }
}   

# Store previous handle list for comparison
# Might not be needed anymore. Keeping it here just in case. :)
$SevenZExe = Get-Item -LiteralPath $SevenZExe

# Prints the PowerShell version table to the console for debugging purposes. This is useful for verifying that the script is running on PowerShell 7, which is required for the use of Foreach-Object -Parallel in the HandleHelper function.
$PSVersionTable

# Actually run the script functions
$didthisrun = PythonScriptsEF
if ($didthisrun -ne 0){
    Write-Host "Error during Python script compilation. Exiting." -ForegroundColor Red
    exit 1
}
else{
    HandleHelper
}



# VERY OLD TESTING CMD.EXE BATCH SCRIPT BELOW, IGNORE. Or dont, I am not your dad.
# If I recall correctly, this was used to test and verify the file handles of the game process, and killing the file handle.
# Doing this caused huge game instability.
#for /F "tokens=3,6 delims=: " %I IN ('C:\test\handle64.exe -accepteula "C:\CCP\EVE Frontier\utopia\code.ccp"') DO "C:\test\handle64.exe" -c %J -y -p %I