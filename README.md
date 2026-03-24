Test Mod Loader for EVE Frontier

```Set-ExecutionPolicy Bypass; .\handle_helper.ps1 -ProcessName exefile.exe -pythonExe C:\Users\username\AppData\Local\Programs\Python\Python312\python.exe -HandleExe .\handle.exe -SevenZExe "C:\Program Files\7-Zip\7z.exe" -mod_folder C:\Users\username\OneDrive\Software\pymemstuff\lemegetonmodloader\mods\SSU_to_Industry -targetserver utopia -recompile $true```
Example Command line 2: Requires powershell 7
```Set-ExecutionPolicy Bypass; pwsh .\handle_helper.ps1 -ProcessName exefile.exe -pythonExe C:\Users\sebor\AppData\Local\Programs\Python\Python312\python.exe -HandleExe .\handle.exe -SevenZExe "C:\Program Files\7-Zip\7z.exe" -mod_folder C:\Users\sebor\OneDrive\Software\GitHub\lemegetonmodloader-POC1\mods\SSU_to_Industry -targetserver utopia -recompile $true -Interval 0.7 -precached false```
