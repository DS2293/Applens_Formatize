# JIRA AUTOMATION TOOL

### Creating .env 
Values to be entered
1. JIRA_URL= https://nwea.atlassian.net/
2. JIRA_EMAIL= Your Jira email address
3. JIRA_API_TOKEN= Your Jira API Token
4. JIRA_WORKLOG_AUTHORS= WorkLog Authors

### BUILD INSTRUCTIONS

### PREREQUISITES

Before building, ensure you have the build tool installed:
`pip install pyinstaller`

### 1. CREATE WINDOWS EXECUTABLE (.exe)

Run this command in your terminal on a **Windows machine**:

`python -m PyInstaller --noconsole --onefile --name JiraAutomationTool main_gui.py`


**OUTPUT:**
You will find the file `JiraAutomationTool.exe` inside the `dist` folder.

### 2. CREATE MAC APPLICATION (.app)

Run this command in your terminal on a **Mac**:

`python3 -m PyInstaller --noconsole --onefile --windowed --name JiraAutomationTool main_gui.py`


**OUTPUT:**
You will find the file `JiraAutomationTool.app` inside the `dist` folder.

**IMPORTANT:** The `--windowed` flag is required on Mac to create a valid application bundle.

## USER GUIDE

### 1. Launch the application.

### 2. Select Conversion Type:

* **"Applens Conversion"**: For standard Ticket ID/Status uploads.

* **"MSM Conversion"**: For detailed monthly tower reporting.

### 3. Click "Browse / Upload" to select your Jira CSV file.

### 4. Click "RUN CONVERSION".

### 5. Use "Clear" to reset fields or "Download Log File" to save reports.
