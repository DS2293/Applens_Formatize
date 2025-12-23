import FreeSimpleGUI as sg
import logging
import os
import shutil
import threading
from datetime import datetime
from dotenv import load_dotenv

# Load env variables at start
load_dotenv()

# Import BOTH pipelines using aliases for clarity
from applens_transformer import run_applens_transformation_pipeline as run_applens
from msm_transformer import run_msm_transformation_pipeline as run_msm
from jira_fetcher import fetch_jira_issues

class GUIHandler(logging.Handler):
    """Sends logs to the GUI."""
    def __init__(self, window_object, key):
        logging.Handler.__init__(self)
        self.window = window_object
        self.key = key

    def emit(self, record):
        log_entry = self.format(record)
        self.window.write_event_value('-LOG-UPDATE-', log_entry + '\n')

def main():
    sg.theme('SystemDefault')

    # Fetch default values from .env (or use empty string/defaults if missing)
    default_url = os.getenv('JIRA_URL', 'https://your-domain.atlassian.net')
    default_email = os.getenv('JIRA_EMAIL', '')
    default_token = os.getenv('JIRA_API_TOKEN', '')

    layout = [
        [sg.Text('Jira Automation Tool', font=('Helvetica', 16), pad=((0,0),(10,20)))],
        
        # SECTION 1: Conversion Type Selection
        [sg.Frame('1. Select Conversion Type', layout=[
            [sg.Radio('Applens Conversion', "RADIO_TYPE", default=True, key='-TYPE-APPLENS-', enable_events=True),
             sg.Radio('MSM Conversion', "RADIO_TYPE", key='-TYPE-MSM-', enable_events=True)]
        ], pad=((0,0),(0,20)), expand_x=True)],
        
        # SECTION 2: Input Source Selection
        [sg.Frame('2. Input Source', layout=[
            [sg.Radio('Upload CSV File', "RADIO_SOURCE", default=True, key='-SRC-FILE-', enable_events=True),
             sg.Radio('Fetch from Jira API', "RADIO_SOURCE", key='-SRC-API-', enable_events=True)],
            
            # --- PANEL A: File Upload ---
            [sg.Column([
                [sg.Text('Select Jira CSV:', size=(15, 1)), 
                 sg.Input(key='-INPUT-FILE-', expand_x=True), 
                 sg.FileBrowse(file_types=(("CSV Files", "*.csv"),))]
            ], key='-PANEL-FILE-', visible=True, expand_x=True)],
            
            # --- PANEL B: API Credentials & Dates ---
            [sg.Column([
                [sg.Text('Jira URL:', size=(10, 1)), sg.Input(default_text=default_url, key='-API-URL-', expand_x=True)],
                [sg.Text('Email:', size=(10, 1)), sg.Input(default_text=default_email, key='-API-EMAIL-', expand_x=True)],
                [sg.Text('API Token:', size=(10, 1)), sg.Input(default_text=default_token, key='-API-TOKEN-', password_char='*', expand_x=True)],
                [sg.Text('_' * 60)],
                # Added enable_events=True to date inputs so we catch manual typing
                [sg.Text('From Date:', size=(10, 1)), 
                 sg.Input(key='-DATE-FROM-', size=(20,1), enable_events=True), 
                 sg.CalendarButton('Select', target='-DATE-FROM-', format='%Y-%m-%d')],
                [sg.Text('To Date:', size=(10, 1)), 
                 sg.Input(key='-DATE-TO-', size=(20,1), enable_events=True), 
                 sg.CalendarButton('Select', target='-DATE-TO-', format='%Y-%m-%d')]
            ], key='-PANEL-API-', visible=False, expand_x=True)]
            
        ], pad=((0,0),(0,20)), expand_x=True)],

        # SECTION 3: Output
        [sg.Frame('3. Output', layout=[
            [sg.Text('Save Output As:', size=(15, 1)), 
             sg.Input(key='-OUTPUT-', default_text='Applens_Upload_Output.xlsx', expand_x=True), 
             sg.FileSaveAs(file_types=(("Excel Files", "*.xlsx"),))]
        ], pad=((0,0),(0,20)), expand_x=True)],

        # Progress & Controls
        [sg.Text('Progress:', font=('Helvetica', 9)), 
         sg.ProgressBar(100, orientation='h', size=(40, 20), key='-PROG-', bar_color=('#4CAF50', '#E0E0E0'), expand_x=True)],

        [sg.Button('RUN PROCESS', size=(20, 2), button_color=('white', '#007BFF'), font=('Helvetica', 10, 'bold'), key='-RUN-'),
         sg.Push(),
         sg.Button('Download Log', size=(15, 2), key='-DOWNLOAD-LOG-'),
         sg.Button('Clear', size=(10, 2), key='-CLEAR-')],

        [sg.Multiline(size=(80, 12), key='-LOG-', autoscroll=True, disabled=True, 
                      font=('Consolas', 9), background_color='#f0f0f0', text_color='black', expand_x=True, expand_y=True)]
    ]

    window = sg.Window('Jira Automation Tool', layout, resizable=True, finalize=True)

    logger = logging.getLogger('ApplensTransformer') 
    gui_handler = GUIHandler(window, '-LOG-')
    gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(gui_handler)

    def update_output_filename(values):
        """Helper to dynamically construct the output filename based on dates and type."""
        start_date = values['-DATE-FROM-']
        end_date = values['-DATE-TO-']
        is_msm = values['-TYPE-MSM-']
        
        # Determine base suffix based on conversion type
        suffix = "MSM_Upload_Output.xlsx" if is_msm else "Applens_Upload_Output.xlsx"
        
        # If dates are present, prepend them
        if start_date and end_date:
            # Format: YYYY-MM-DD_YYYY-MM-DD_Type_Upload_Output.xlsx
            # Replacing invalid filename chars just in case user typed slashes
            s_clean = start_date.replace('/', '-').replace('\\', '-')
            e_clean = end_date.replace('/', '-').replace('\\', '-')
            new_name = f"{s_clean}_to_{e_clean}_{suffix}"
        else:
            # Fallback if no dates
            new_name = suffix
            
        window['-OUTPUT-'].update(new_name)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        
        # Toggle Visibility based on Source Selection
        if event == '-SRC-FILE-':
            window['-PANEL-FILE-'].update(visible=True)
            window['-PANEL-API-'].update(visible=False)
        
        if event == '-SRC-API-':
            window['-PANEL-FILE-'].update(visible=False)
            window['-PANEL-API-'].update(visible=True)

        # EVENT: Auto-Update Output Filename based on Radio Selection OR Dates
        if event in ('-TYPE-MSM-', '-TYPE-APPLENS-', '-DATE-FROM-', '-DATE-TO-'):
            # Only update filename automatically if we are in API mode (since dates matter there)
            # OR if the user is just switching types.
            if values['-SRC-API-'] or event in ('-TYPE-MSM-', '-TYPE-APPLENS-'):
                update_output_filename(values)

        if event == '-LOG-UPDATE-':
            log_msg = values[event]
            window['-LOG-'].update(log_msg, append=True)
            if "Phase 1" in log_msg: window['-PROG-'].update(25)
            elif "Phase 2" in log_msg: window['-PROG-'].update(50)
            elif "Phase 3" in log_msg: window['-PROG-'].update(75)
            elif "SUCCESS" in log_msg: window['-PROG-'].update(100)
            elif "failed" in log_msg.lower(): window['-PROG-'].update(0)

        if event == '-RUN-':
            output_path = values['-OUTPUT-']
            is_msm = values['-TYPE-MSM-']
            
            if values['-SRC-FILE-']:
                input_file = values['-INPUT-FILE-']
                if not input_file:
                    sg.popup_error("Please select a CSV file.")
                    continue
                
                window['-RUN-'].update(disabled=True, text='Processing...')
                window['-PROG-'].update(0)
                threading.Thread(target=run_wrapper_file, args=(input_file, output_path, is_msm, window), daemon=True).start()
                
            else:
                api_url = values['-API-URL-']
                api_email = values['-API-EMAIL-']
                api_token = values['-API-TOKEN-']
                date_from = values['-DATE-FROM-']
                date_to = values['-DATE-TO-']
                
                if not all([api_url, api_email, api_token, date_from, date_to]):
                    sg.popup_error("Please fill in all API credentials and Date fields.")
                    continue
                
                window['-RUN-'].update(disabled=True, text='Fetching & Processing...')
                window['-PROG-'].update(0)
                threading.Thread(target=run_wrapper_api, args=(api_url, api_email, api_token, date_from, date_to, output_path, is_msm, window), daemon=True).start()

        if event == '-THREAD-DONE-':
            window['-RUN-'].update(disabled=False, text='RUN PROCESS')
            sg.popup("Process Completed!", "Check logs for details.", title="Success")

        if event == '-CLEAR-':
            for key in ['-INPUT-FILE-', '-DATE-FROM-', '-DATE-TO-']:
                window[key].update('')
            window['-API-URL-'].update(default_url)
            window['-API-EMAIL-'].update(default_email)
            window['-API-TOKEN-'].update(default_token)
            
            # Reset output name to default without dates
            default_out = 'MSM_Upload_Output.xlsx' if values['-TYPE-MSM-'] else 'Applens_Upload_Output.xlsx'
            window['-OUTPUT-'].update(default_out)
            
            window['-PROG-'].update(0)
        
        if event == '-DOWNLOAD-LOG-':
            log_files = ['applens_conversion.log', 'msm_conversion.log']
            found_logs = [f for f in log_files if os.path.exists(f)]
            if found_logs:
                latest = max(found_logs, key=os.path.getmtime)
                save = sg.popup_get_file('Save Log', save_as=True, file_types=(("Text", "*.log"),))
                if save: shutil.copy(latest, save)

    window.close()

def run_wrapper_file(input_path, output_path, is_msm, window):
    if is_msm: run_msm(input_path, output_path)
    else: run_applens(input_path, output_path)
    window.write_event_value('-THREAD-DONE-', '')

def run_wrapper_api(url, email, token, start, end, output_path, is_msm, window):
    temp_csv = "Jira_API_Dump.csv"
    success = fetch_jira_issues(url, email, token, start, end, temp_csv)
    
    if success:
        if is_msm: run_msm(temp_csv, output_path)
        else: run_applens(temp_csv, output_path)
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
            
    window.write_event_value('-THREAD-DONE-', '')

if __name__ == '__main__':
    main()