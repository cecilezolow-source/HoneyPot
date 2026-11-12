@echo off
chcp 65001 >nul
echo HoneyPot-Datenbank wird gestoppt...
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqladmin.exe" -u root --host=127.0.0.1 --port=3306 shutdown
echo Fertig. Die Datenbank läuft jetzt nicht mehr.
pause
