@echo off
echo Creating shortcut...
powershell "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('C:\Users\Sudh\Desktop\FLVCS.lnk'); $s.TargetPath = 'd:\FIVCS-git\Flvcs-Client\dist\FLVCS.exe'; $s.WorkingDirectory = 'd:\FIVCS-git\Flvcs-Client\dist'; $s.IconLocation = 'd:\FIVCS-git\Flvcs-Client\dist\FLVCS.exe'; $s.Save()"
echo Shortcut created on desktop.
pause
