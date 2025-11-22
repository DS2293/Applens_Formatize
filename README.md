Build Instructions

Prerequisites

Before building, ensure you have the build tool installed on your system:

pip install pyinstaller

1. Create Windows Executable (.exe)

Run this command in your terminal on a Windows machine:

python -m PyInstaller --noconsole --onefile --name JiraToApplens main_gui.py

Output:
You will find JiraToApplens.exe in the dist/ folder.

2. Create Mac Application (.app)

Run this command in your terminal on a Mac:

python3 -m PyInstaller --noconsole --onefile --windowed --name JiraToApplens main_gui.py

Output:
You will find JiraToApplens.app in the dist/ folder.

Note: The --windowed flag is critical for Mac to create a proper application bundle instead of a command-line binary.