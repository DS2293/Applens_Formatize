# JIRA AUTOMATION TOOL

# BUILD INSTRUCTIONS

## PREREQUISITES

Before building, ensure you have the build tool installed:
`pip install pyinstaller`

## 1. CREATE WINDOWS EXECUTABLE (.exe)

Run this command in your terminal on a **Windows machine**:

Here is the raw content of the `README.txt` file, including all standard Markdown symbols as requested. You can copy this block directly.

```text
# JIRA AUTOMATION TOOL

# BUILD INSTRUCTIONS

## PREREQUISITES

Before building, ensure you have the build tool installed:
`pip install pyinstaller`

## 1. CREATE WINDOWS EXECUTABLE (.exe)

Run this command in your terminal on a **Windows machine**:

```

python -m PyInstaller --noconsole --onefile --name JiraAutomationTool main\_gui.py

```

**OUTPUT:**
You will find the file `JiraAutomationTool.exe` inside the `dist` folder.

## USER GUIDE

### 1. Launch the application.

### 2. Select Conversion Type:

* **"Applens Conversion"**: For standard Ticket ID/Status uploads.

* **"MSM Conversion"**: For detailed monthly tower reporting.

### 3. Click "Browse / Upload" to select your Jira CSV file.

### 4. Click "RUN CONVERSION".

### 5. Use "Clear" to reset fields or "Download Log File" to save reports.
```