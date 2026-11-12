@echo off
chcp 65001 >nul
title HoneyPot MySQL  -  Fenster offen lassen = Datenbank läuft
echo ==========================================================
echo   HoneyPot-Datenbank wird gestartet...
echo   Dieses Fenster bitte offen lassen, solange du die DB brauchst.
echo   Zum Stoppen: Fenster schließen oder Strg+C drücken,
echo   oder datenbank-stoppen.bat doppelklicken.
echo ==========================================================
echo.
"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --datadir="C:\Users\cecil\AppData\Local\mysql-honeypot\data" --port=3306 --console
echo.
echo Datenbank wurde beendet.
pause
