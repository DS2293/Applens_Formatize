import pandas as pd
import logging
import os
from typing import Optional, List, Dict

# --- CONFIGURATION & CONSTANTS ---

# Mapping: { Jira_Column (Source) : Applens_Column (Target) }
COLUMN_MAPPING: Dict[str, str] = {
    'Issue Key': 'Ticket ID',
    'Issue Type': 'Ticket Type',
    'Updated': 'Open Date',
    'Status': 'Status',
    'Resolved': 'Closed Date'
}

# Static values to be applied to every row
CONSTANTS: Dict[str, str] = {
    'Priority': 'NONE',
    'Application': 'HMOF',
    'Assignment Group': 'HMH Support Group'
}

# The strictly enforced order of columns for the final output
FINAL_COLUMN_ORDER: List[str] = [
    'Ticket ID', 'Ticket Type', 'Open Date', 'Priority',
    'Status', 'Application', 'Assignment Group', 'Closed Date'
]

# --- LOGGING SETUP ---

def setup_logger(name: str = 'ApplensTransformer') -> logging.Logger:
    """
    Configures a logger that streams to the terminal (console).
    It also writes to a file for audit purposes.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if function is called repeatedly
    if not logger.handlers:
        # 1. Console Handler (Logs to Terminal)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. File Handler (Logs to File)
        file_handler = logging.FileHandler('applens_conversion.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Initialize logger for this module
logger = setup_logger()

# --- CORE FUNCTIONS ---

def load_source_data(file_path: str) -> Optional[pd.DataFrame]:
    """
    Reads the raw Jira dump from a CSV file.
    Optimization: Only loads the specific columns defined in COLUMN_MAPPING keys.
    Update: Handles CASE-INSENSITIVE column matching (e.g., 'issue key' matches 'Issue Key').
    """
    logger.info(f"Phase 1: Reading input CSV file from {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    try:
        # STEP 1: Read only the header row to check column names dynamically
        try:
            header_df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
        except UnicodeDecodeError:
            header_df = pd.read_csv(file_path, nrows=0, encoding='latin1')
            
        actual_file_columns = list(header_df.columns)
        
        # Create a dictionary map: {lowercase_name : actual_name_in_file}
        # Example: {'issue key': 'issue KEY', 'status': 'Status'}
        actual_col_map = {col.lower().strip(): col for col in actual_file_columns}
        
        usecols_actual = []
        normalization_map = {} # Maps actual file col -> Standard Expected col
        missing_cols = []
        
        # Check for each required column in a case-insensitive way
        for required_col in COLUMN_MAPPING.keys():
            req_lower = required_col.lower().strip()
            
            if req_lower in actual_col_map:
                actual_name = actual_col_map[req_lower]
                usecols_actual.append(actual_name)
                # We must normalize the name later so the rest of the script works
                normalization_map[actual_name] = required_col
            else:
                missing_cols.append(required_col)
        
        if missing_cols:
            error_msg = f"Missing required columns (checked case-insensitive): {missing_cols}. Found headers: {actual_file_columns}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # STEP 2: Read the data using the ACTUAL column names found in the file
        try:
            df = pd.read_csv(file_path, usecols=usecols_actual, encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed, retrying with latin1 encoding.")
            df = pd.read_csv(file_path, usecols=usecols_actual, encoding='latin1')

        # STEP 3: Normalize column names to the standard Title Case expected by the rest of the script
        # Example: Renames 'issue KEY' -> 'Issue Key'
        df = df.rename(columns=normalization_map)

        logger.info(f"Successfully loaded {len(df)} rows.")
        return df
        
    except ValueError as e:
        logger.error(str(e))
        raise e
    except Exception as e:
        logger.critical(f"Failed to read CSV file: {str(e)}")
        raise e

def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames columns and injects constant values.
    """
    logger.info("Phase 2: Applying transformations...")
    
    # 1. Rename Columns
    df_transformed = df.rename(columns=COLUMN_MAPPING)
    
    # 2. Inject Constants
    for col, val in CONSTANTS.items():
        df_transformed[col] = val
        
    return df_transformed

def validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes dates and handles missing required data.
    """
    logger.info("Phase 3: Validating data...")
    
    # 1. Drop rows where Ticket ID is missing
    initial_count = len(df)
    df = df.dropna(subset=['Ticket ID'])
    if len(df) < initial_count:
        logger.warning(f"Dropped {initial_count - len(df)} rows due to missing Ticket IDs.")

    # 2. Standardize Date Formats
    date_cols = ['Open Date', 'Closed Date']
    
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # 3. Clean Nulls in 'Closed Date'
    df['Closed Date'] = df['Closed Date'].fillna('')
    
    logger.info("Validation complete.")
    return df

def save_target_file(df: pd.DataFrame, output_path: str) -> bool:
    """
    Writes the final DataFrame to Excel (.xlsx).
    """
    logger.info(f"Phase 4: Writing output to {output_path}")
    
    try:
        # Ensure strict column order
        df_final = df[FINAL_COLUMN_ORDER]
        
        df_final.to_excel(output_path, index=False)
        logger.info("SUCCESS: Transformation complete.")
        return True
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")
        return False

# --- PUBLIC API ---

def run_transformation_pipeline(input_path: str, output_path: str) -> bool:
    """
    The Main Entry Point.
    """
    try:
        df = load_source_data(input_path)
        df = apply_transformations(df)
        df = validate_and_clean(df)
        success = save_target_file(df, output_path)
        return success
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return False

# --- EXECUTION BLOCK (Runs when you execute this file directly) ---
if __name__ == "__main__":
    # Define the file names you want to use
    INPUT_FILE = 'Jira_Dump_Input.csv'
    OUTPUT_FILE = 'Applens_Upload_Output.xlsx'

    print(f"--- Starting Direct Execution ---")
    
    if os.path.exists(INPUT_FILE):
        print(f"Processing file: {INPUT_FILE}")
        success = run_transformation_pipeline(INPUT_FILE, OUTPUT_FILE)
        
        if success:
            print(f"\nSUCCESS! Output saved to: {OUTPUT_FILE}")
        else:
            print("\nFAILURE. Please check the logs printed above or in 'applens_conversion.log'.")
    else:
        print(f"\nERROR: Input file '{INPUT_FILE}' not found.")
        print("Please rename your CSV file to 'Jira_Dump_Input.csv' and try again.")