import FreeSimpleGUI as sg
import logging
import os
import shutil
import threading
from applens_transformer import run_applens_transformation_pipeline as run_applens
from msm_transformer import run_msm_transformation_pipeline as run_msm

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

    layout = [
        [sg.Text('Jira Automation Tool', font=('Helvetica', 16), pad=((0,0),(10,20)))],
        
        # SECTION 1: Conversion Type Selection
        [sg.Frame('1. Select Conversion Type', layout=[
            [sg.Radio('Applens Conversion', "RADIO1", default=True, key='-TYPE-APPLENS-', enable_events=True),
             sg.Radio('MSM Conversion', "RADIO1", key='-TYPE-MSM-', enable_events=True)]
        ], pad=((0,0),(0,20)), expand_x=True)],
        
        # SECTION 2: File Selection
        [sg.Frame('2. Input & Output', layout=[
            [sg.Text('Select Jira Dump (.csv):', size=(20, 1)), 
             sg.Input(key='-INPUT-', expand_x=True), 
             sg.FileBrowse(button_text='Browse / Upload', file_types=(("CSV Files", "*.csv"),))],
            
            [sg.Text('Save Output As (.xlsx):', size=(20, 1)), 
             sg.Input(key='-OUTPUT-', default_text='Applens_Upload_Output.xlsx', expand_x=True), 
             sg.FileSaveAs(button_text='Browse Save Location', file_types=(("Excel Files", "*.xlsx"),))]
        ], pad=((0,0),(0,20)), expand_x=True)],

        # Progress Bar
        [sg.Text('Progress:', font=('Helvetica', 9)), 
         sg.ProgressBar(100, orientation='h', size=(40, 20), key='-PROG-', bar_color=('#4CAF50', '#E0E0E0'), expand_x=True)],

        # Buttons
        [sg.Button('RUN CONVERSION', size=(20, 2), button_color=('white', '#007BFF'), font=('Helvetica', 10, 'bold'), key='-RUN-'),
         sg.Push(),
         sg.Button('Download Log File', size=(15, 2), key='-DOWNLOAD-LOG-'),
         sg.Button('Clear', size=(10, 2), key='-CLEAR-')],

        # Logs
        [sg.Text('Process Logs:', pad=((0,0),(10,5)))],
        [sg.Multiline(size=(80, 15), key='-LOG-', autoscroll=True, disabled=True, 
                      font=('Consolas', 9), background_color='#f0f0f0', text_color='black', expand_x=True, expand_y=True)]
    ]

    window = sg.Window('Jira Automation Tool', layout, resizable=True, finalize=True)

    # Connect Logger
    # We attach the handler to the root logger to capture logs from BOTH modules
    logger = logging.getLogger('ApplensTransformer') 
    gui_handler = GUIHandler(window, '-LOG-')
    gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(gui_handler)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break

        # EVENT: Update Output Filename based on Selection
        if event == '-TYPE-MSM-':
            # If user switches to MSM, update default filename
            if values['-OUTPUT-'] == 'Applens_Upload_Output.xlsx':
                window['-OUTPUT-'].update('MSM_Upload_Output.xlsx')
        
        if event == '-TYPE-APPLENS-':
            # If user switches back to Applens, update default filename
            if values['-OUTPUT-'] == 'MSM_Upload_Output.xlsx':
                window['-OUTPUT-'].update('Applens_Upload_Output.xlsx')

        if event == '-LOG-UPDATE-':
            log_msg = values[event]
            window['-LOG-'].update(log_msg, append=True)
            
            # Progress Bar Logic
            if "Phase 1" in log_msg:
                window['-PROG-'].update(25)
            elif "Phase 2" in log_msg:
                window['-PROG-'].update(50)
            elif "Phase 3" in log_msg:
                window['-PROG-'].update(75)
            elif "Phase 4" in log_msg:
                window['-PROG-'].update(90)
            elif "SUCCESS" in log_msg:
                window['-PROG-'].update(100)
            elif "failed" in log_msg.lower() or "error" in log_msg.lower():
                window['-PROG-'].update(0)

        # EVENT: Run Conversion
        if event == '-RUN-':
            input_path = values['-INPUT-']
            output_path = values['-OUTPUT-']
            is_msm = values['-TYPE-MSM-'] # True if MSM is selected

            if not input_path:
                sg.popup_error("Please select a Jira input file first.")
                continue
            if not output_path:
                sg.popup_error("Please specify an output file path.")
                continue
            
            window['-RUN-'].update(disabled=True, text='Processing...')
            window['-PROG-'].update(0) 
            
            try:
                # Pass the 'is_msm' flag to the wrapper
                threading.Thread(target=run_wrapper, args=(input_path, output_path, is_msm, window), daemon=True).start()
            except Exception as e:
                logger.error(f"Failed to start process: {e}")
                window['-RUN-'].update(disabled=False, text='RUN CONVERSION')

        # EVENT: Thread Finished
        if event == '-THREAD-DONE-':
            window['-RUN-'].update(disabled=False, text='RUN CONVERSION')
            sg.popup("Process Completed!", "Check the logs for details.", title="Success")

        # EVENT: Clear Fields
        if event == '-CLEAR-':
            window['-INPUT-'].update('')
            # Reset output name based on current selection
            default_out = 'MSM_Upload_Output.xlsx' if values['-TYPE-MSM-'] else 'Applens_Upload_Output.xlsx'
            window['-OUTPUT-'].update(default_out)
            window['-PROG-'].update(0)
            window['-RUN-'].update(disabled=False, text='RUN CONVERSION')

        # EVENT: Download Logs
        if event == '-DOWNLOAD-LOG-':
            # Check for either log file
            log_files = ['applens_conversion.log', 'msm_conversion.log']
            found_logs = [f for f in log_files if os.path.exists(f)]
            
            if not found_logs:
                sg.popup_error("No log files found yet. Run a conversion first.")
                continue

            # Default to the most recently modified log
            latest_log = max(found_logs, key=os.path.getmtime)
            
            save_path = sg.popup_get_file('Save Log File As', save_as=True, file_types=(("Text Files", "*.log;*.txt"),))
            if save_path:
                try:
                    shutil.copy(latest_log, save_path)
                    sg.popup_quick_message(f"Log saved to {save_path}", background_color='green', text_color='white')
                except Exception as e:
                    sg.popup_error(f"Failed to save log: {e}")

    window.close()

def run_wrapper(input_path, output_path, is_msm, window):
    """
    Wrapper function that decides which pipeline to run based on user selection.
    """
    if is_msm:
        # Run MSM Pipeline
        run_msm(input_path, output_path)
    else:
        # Run Applens Pipeline
        run_applens(input_path, output_path)
        
    window.write_event_value('-THREAD-DONE-', '')

if __name__ == '__main__':
    main()