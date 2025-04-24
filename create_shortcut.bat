@echo off
echo Creating shortcut...
powershell "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('C:\Users\Sudh\Desktop\FLVCS.lnk'); $s.TargetPath = 'D:\FIVCS-git\Flvcs-Client\dist\FLVCS.exe'; $s.WorkingDirectory = 'D:\FIVCS-git\Flvcs-Client\dist'; $s.IconLocation = 'D:\FIVCS-git\Flvcs-Client\dist\FLVCS.exe'; $s.Save()"
echo Shortcut created on desktop.
pause 