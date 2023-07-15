@echo off

REM Install script for samftp.py on Windows

REM Step 1: Install Python if not already installed
REM TODO: Add commands to check and install Python if needed

REM Step 2: Install required packages using pip
pip install --user requests~=2.26.0
pip install --user beautifulsoup4==4.12.2
pip install --user pyfzf~=0.3.1

REM Step 3: Copy the script to the desired location
set DESTINATION_FOLDER=%APPDATA%\Python\Scripts
copy "samftp.py" %DESTINATION_FOLDER%

REM Step 4: Add the shebang for Python 3 to the script
echo #!%APPDATA%\Python\Python39\python.exe > %DESTINATION_FOLDER%\samftp.py.tmp
type %DESTINATION_FOLDER%\samftp.py >> %DESTINATION_FOLDER%\samftp.py.tmp
move /y %DESTINATION_FOLDER%\samftp.py.tmp %DESTINATION_FOLDER%\samftp.py

echo Installation completed.
