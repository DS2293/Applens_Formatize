import os
import logging
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Setup logging
logger = logging.getLogger("ApplensTransformer")

def fetch_jira_issues(base_url, email, api_token, start_date, end_date, output_csv_path):
    """
    Fetch issues from Jira using a POST request to handle long JQL queries.
    Uses the modern /rest/api/3/search/jql endpoint with cursor-based pagination
    to avoid 410 errors from the deprecated offset-based API.
    """
    # 1. Validation & Setup
    if not base_url: base_url = os.getenv("JIRA_URL")
    if not email: email = os.getenv("JIRA_EMAIL")
    if not api_token: api_token = os.getenv("JIRA_API_TOKEN")
    
    # Retrieve the author list from the environment
    authors = os.getenv("JIRA_WORKLOG_AUTHORS")

    if not all([base_url, email, api_token]):
        msg = "Missing Jira credentials. Check .env file."
        logger.error(msg)
        raise ValueError(msg)
        
    if not authors:
        msg = "Missing JIRA_WORKLOG_AUTHORS in .env file."
        logger.error(msg)
        raise ValueError(msg)

    base_url = base_url.rstrip("/")
    logger.info(f"Connecting to Jira: {base_url}")

    # 2. Build Long JQL Query
    # We must ensure the dates are in a format JQL accepts (YYYY/MM/DD or YYYY-MM-DD).
    # Assuming inputs start_date/end_date are already valid strings like '2025-12-01'.
    jql = (
        f"timespent is not null AND worklogAuthor in ({authors}) "
        f"AND worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'"
    )
    logger.info(f"JQL Length: {len(jql)} chars")

    # 3. Configure Search API (POST) - MIGRATED to /jql endpoint
    search_url = f"{base_url}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(email, api_token)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Define fields to fetch - essential for your transformers
    fields_to_fetch = [
        "key", "issuetype", "updated", "status", "resolutiondate", 
        "project", "summary", "assignee", "priority", "created", 
        "worklog", "timespent", "customfield_12345" # Added timespent explicitly
    ]

    all_issues = []
    max_results = 100 # Batch size
    next_page_token = None

    try:
        while True:
            # Log pagination progress
            if next_page_token:
                logger.info(f"Fetching page with token: {next_page_token[:10]}...")
            else:
                logger.info(f"Fetching first page...")
            
            payload = {
                "jql": jql,
                "maxResults": max_results,
                "fields": fields_to_fetch
            }
            
            # Use nextPageToken for pagination if available
            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = requests.post(search_url, headers=headers, json=payload, auth=auth)

            if response.status_code != 200:
                error_msg = f"Jira API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            data = response.json()
            issues = data.get('issues', [])
            next_page_token = data.get('nextPageToken') # Get token for next page
            
            if not issues:
                break
            
            all_issues.extend(issues)
            
            # If no next_page_token, we are done
            if not next_page_token:
                break

        logger.info(f"Total issues fetched: {len(all_issues)}")
        
        if not all_issues:
            logger.warning("No tickets found matching criteria.")
            return False

        # 4. Flatten JSON to CSV format
        parsed_data = []
        for issue in all_issues:
            fields = issue.get('fields', {})
            
            # Helper for nested dicts (e.g. priority.name)
            def get_val(key, subkey='name'):
                val = fields.get(key)
                if isinstance(val, dict): return val.get(subkey, '')
                return val if val else ''

            row = {
                'Issue Key': issue.get('key'),
                'Issue Type': get_val('issuetype'),
                'Updated': fields.get('updated'),
                'Status': get_val('status'),
                'Resolved': fields.get('resolutiondate'),
                'Project Name': get_val('project'),
                'Summary': fields.get('summary'),
                'Assignee': get_val('assignee', 'displayName'),
                'Priority': get_val('priority'),
                'Created': fields.get('created'),
                'Platform': get_val('customfield_12345'),
                # Using timespent field directly
                'Worklog': fields.get('timespent', 0) if fields.get('timespent') else 0
            }
            parsed_data.append(row)

        # 5. Save to CSV
        df = pd.DataFrame(parsed_data)
        
        # Datetime timezone fix for Excel compatibility
        date_cols = ["Updated", "Resolved", "Created"]
        for col in date_cols:
            if col in df.columns:
                # Force conversion to datetime objects first
                df[col] = pd.to_datetime(df[col], errors='coerce')
                # Then remove timezone info safely
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.tz_localize(None)

        df.to_csv(output_csv_path, index=False)
        logger.info(f"Saved Jira dump to {output_csv_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch from Jira: {str(e)}")
        raise e