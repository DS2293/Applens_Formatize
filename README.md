# JIRA TO APPLENS CONVERTER
## BUILD INSTRUCTIONS

### PREREQUISITES
Before building, ensure you have the build tool installed. Run this command:
`pip install pyinstaller`

---

### 1. CREATE WINDOWS EXECUTABLE (.exe)
Run this command in your terminal on a **Windows machine**:

`python -m PyInstaller --noconsole --onefile --name JiraToApplens main_gui.py`

**OUTPUT:**
You will find the file **JiraToApplens.exe** inside the **dist** folder.

---

### 2. CREATE MAC APPLICATION (.app)
Run this command in your terminal on a **Mac**:

`python3 -m PyInstaller --noconsole --onefile --windowed --name JiraToApplens main_gui.py`

**OUTPUT:**
You will find the file **JiraToApplens.app** inside the **dist** folder.

Note: The --windowed flag is critical for Mac to create a proper application bundle instead of a command-line binary.