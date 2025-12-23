# JIRA AUTOMATION TOOL

## 1. Creating .env 
Values to be entered
  
     JIRA_URL= https://nwea.atlassian.net/  
     JIRA_EMAIL= Your Jira email address  
     JIRA_API_TOKEN= Your Jira API Token  
     JIRA_WORKLOG_AUTHORS= WorkLog Authors  

## 2. BUILD INSTRUCTIONS

### PREREQUISITES

Before building, ensure you have the build tool installed:
`pip install pyinstaller`

### 1. CREATE WINDOWS EXECUTABLE (.exe)

Run this command in your terminal on a **Windows machine**:  
`python -m PyInstaller --noconsole --onefile --name JiraAutomationTool main_gui.py`


**OUTPUT:**
You will find the file `JiraAutomationTool.exe` inside the `dist` folder.

### 2. CREATE MAC APPLICATION (.app)

R un this command in your terminal on a **Mac**:  
`python3 -m PyInstaller --noconsole --onefile --windowed --name JiraAutomationTool main_gui.py`


**OUTPUT:**
You will find the file `JiraAutomationTool.app` inside the `dist` folder.

**IMPORTANT:** The `--windowed` flag is required on Mac to create a valid application bundle.

