@echo off
title SITS Data Sync Tool
echo Closing old connections and updating database...
echo.
python master_data_sync.py
echo.
echo ==========================================
echo SUCCESS: Database has been rebuilt.
echo Please go to your browser and press 'R'.
echo ==========================================
pause