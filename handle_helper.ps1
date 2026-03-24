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
.PARAMETER precached
    $precached is a boolean flag that determines whether the mod files should be precached on each run. Set to $true to enable precaching, or $false to skip it.
.PARAMETER interval
    $Interval is a int value that determines the sleep interval (in seconds) between checks for the process and file handles. Default is 33 seconds.
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
    [float]$Interval = 33
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
        }
    }
    return 0
}

function HandleHelper(){
    Write-Host "Monitoring file handles for process: $ProcessName" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
    while ($true) {
        try{
            $test = Get-WmiObject Win32_Process -Filter "Name = 'exefile.exe'" | Select-Object Name, ProcessId, CommandLine
            $pids = $test.ProcessId
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
                    $sw.Stop()
                    Write-Output "Total time elapsed: $($sw.Elapsed.TotalSeconds) seconds"
                    Write-Host "attempt" -ForegroundColor Yellow
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
$SevenZExe = Get-Item -LiteralPath $SevenZExe
$PSVersionTable
PythonScriptsEF
HandleHelper



#for /F "tokens=3,6 delims=: " %I IN ('C:\test\handle64.exe -accepteula "C:\CCP\EVE Frontier\utopia\code.ccp"') DO "C:\test\handle64.exe" -c %J -y -p %I