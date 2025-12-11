import pandas as pd
import logging
import os
from typing import Optional, List, Dict

# --- CONFIGURATION ---

# Mapping: { Source_Column_In_Jira : Target_Column_In_Applens }
# Source keys are treated as case-insensitive during read
COLUMN_MAPPING: Dict[str, str] = {
    'Issue Key': 'Ticket ID',
    'Issue Type': 'Ticket Type',
    'Updated': 'Open Date',
    'Status': 'Status',
    'Resolved': 'Closed Date'
}

CONSTANTS: Dict[str, str] = {
    'Priority': 'NONE',
    'Application': 'HMOF',
    'Assignment Group': 'HMH Support Group'
}

# Strict output order required by Applens
FINAL_COLUMN_ORDER: List[str] = [
    'Ticket ID', 'Ticket Type', 'Open Date', 'Priority',
    'Status', 'Application', 'Assignment Group', 'Closed Date'
]

# --- LOGGING ---

def setup_logger(name: str = 'ApplensTransformer') -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (delay=True prevents empty files on import)
        file_handler = logging.FileHandler('applens_conversion.log', delay=True)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()

# --- PIPELINE FUNCTIONS ---

def load_source_data(file_path: str) -> Optional[pd.DataFrame]:
    logger.info(f"Phase 1: Reading input CSV file from {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    try:
        # Check headers first to determine actual column names (handling case sensitivity)
        try:
            header_df = pd.read_csv(file_path, nrows=0, encoding='utf-8')
        except UnicodeDecodeError:
            header_df = pd.read_csv(file_path, nrows=0, encoding='latin1')
            
        actual_file_columns = list(header_df.columns)
        actual_col_map = {col.lower().strip(): col for col in actual_file_columns}
        
        usecols_actual = []
        normalization_map = {}
        missing_cols = []
        
        for required_col in COLUMN_MAPPING.keys():
            req_lower = required_col.lower().strip()
            if req_lower in actual_col_map:
                actual_name = actual_col_map[req_lower]
                usecols_actual.append(actual_name)
                normalization_map[actual_name] = required_col
            else:
                missing_cols.append(required_col)
        
        if missing_cols:
            error_msg = f"Missing required columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Read only required columns
        try:
            df = pd.read_csv(file_path, usecols=usecols_actual, encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed, retrying with latin1.")
            df = pd.read_csv(file_path, usecols=usecols_actual, encoding='latin1')

        # Normalize headers to standard names
        df = df.rename(columns=normalization_map)

        logger.info(f"Successfully loaded {len(df)} rows.")
        return df
        
    except Exception as e:
        logger.critical(f"Failed to read CSV file: {str(e)}")
        raise e

def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Phase 2: Applying transformations...")
    
    df_transformed = df.rename(columns=COLUMN_MAPPING)
    
    for col, val in CONSTANTS.items():
        df_transformed[col] = val
        
    return df_transformed

def validate_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Phase 3: Validating data...")
    
    # Drop rows missing Ticket ID
    initial_count = len(df)
    df = df.dropna(subset=['Ticket ID'])
    if len(df) < initial_count:
        logger.warning(f"Dropped {initial_count - len(df)} rows due to missing Ticket IDs.")

    # IMPORTANT CHANGE:
    # Do NOT convert dates to datetime – keep Jira's original string format.
    # This avoids timezone-aware datetime issues when writing to Excel
    # and keeps the "default Jira" textual representation.
    #
    # (Old code removed):
    # date_cols = ['Open Date', 'Closed Date']
    # for col in date_cols:
    #      if col in df.columns:
    #          df[col] = pd.to_datetime(df[col], errors='coerce')

    # Handle nulls in Closed Date for visual cleanliness (still as strings)
    if 'Closed Date' in df.columns:
        df['Closed Date'] = df['Closed Date'].fillna('')

    logger.info("Validation complete.")
    return df

def save_target_file(df: pd.DataFrame, output_path: str) -> bool:
    logger.info(f"Phase 4: Writing output to {output_path}")
    
    try:
        df_final = df[FINAL_COLUMN_ORDER]
        # Since we keep dates as strings, there should be no timezone-aware datetimes.
        df_final.to_excel(output_path, index=False)
        logger.info("SUCCESS: Transformation complete.")
        return True
    except Exception as e:
        logger.error(f"Failed to write output file: {e}")
        return False

def run_applens_transformation_pipeline(input_path: str, output_path: str) -> bool:
    try:
        df = load_source_data(input_path)
        df = apply_transformations(df)
        df = validate_and_clean(df)
        success = save_target_file(df, output_path)
        return success
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Direct execution block for testing
    INPUT_FILE = 'Jira_Dump_Input.csv'
    OUTPUT_FILE = 'Applens_Upload_Output.xlsx'

    print(f"--- Starting Direct Execution Mode ---")
    
    if os.path.exists(INPUT_FILE):
        print(f"Processing file: {INPUT_FILE}")
        success = run_applens_transformation_pipeline(INPUT_FILE, OUTPUT_FILE)
        if success:
            print(f"\nSUCCESS! Output saved to: {OUTPUT_FILE}")
        else:
            print("\nFAILURE. Please check the logs.")
    else:
        print(f"\nNOTE: No input file '{INPUT_FILE}' found.")