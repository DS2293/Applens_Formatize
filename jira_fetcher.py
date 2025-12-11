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
    Fetch issues from Jira within a date range and save them to a CSV file.
    Uses the new Jira Cloud enhanced search endpoint: GET /rest/api/3/search/jql
    """
    # Fallback to environment variables if arguments are missing
    if not base_url:
        base_url = os.getenv("JIRA_URL")
    if not email:
        email = os.getenv("JIRA_EMAIL")
    if not api_token:
        api_token = os.getenv("JIRA_API_TOKEN")

    if not base_url or not email or not api_token:
        msg = "Missing Jira configuration. Ensure base_url, email, and api_token are provided."
        logger.error(msg)
        raise ValueError(msg)

    # Normalize base URL (avoid trailing slash)
    base_url = base_url.rstrip("/")
    logger.info(f"Connecting to Jira: {base_url}")

    # 1. Build JQL for the date range
    jql = f'updated >= "{start_date}" AND updated <= "{end_date}" ORDER BY updated DESC'
    logger.info(f"Using JQL: {jql}")

    # 2. Fields to retrieve
    requested_fields = [
        "issuetype", "updated", "status", "resolutiondate", "project", 
        "summary", "assignee", "priority", "created", "worklog", 
        "customfield_12345"
    ]
    fields_param = ",".join(requested_fields)

    # 3. Jira search endpoint
    search_url = f"{base_url}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(email, api_token)
    headers = {"Accept": "application/json"}

    all_issues = []
    max_results = 1000
    next_page_token = None
    page_count = 0
    max_pages = 50 

    try:
        while True:
            page_count += 1
            if page_count == 1:
                logger.info("Fetching first page of results...")
            else:
                logger.info(f"Fetching page {page_count} with nextPageToken={next_page_token}...")

            params = {
                "jql": jql,
                "maxResults": max_results,
                "fields": fields_param,
            }
            if next_page_token:
                params["nextPageToken"] = next_page_token

            response = requests.get(search_url, headers=headers, params=params, auth=auth)

            if response.status_code != 200:
                error_msg = f"Jira API Error {response.status_code}: {response.text[:500]}..."
                logger.error(error_msg)
                raise Exception(error_msg)

            data = response.json()
            issues = data.get("issues", [])
            is_last = data.get("isLast", True)
            next_page_token = data.get("nextPageToken")

            logger.info(f"Received {len(issues)} issues in page {page_count}.")

            if not issues:
                break

            all_issues.extend(issues)

            if is_last or not next_page_token:
                break

            if page_count >= max_pages:
                logger.warning(f"Reached max pages limit ({max_pages}). Stopping.")
                break

        logger.info(f"Total issues fetched: {len(all_issues)}")

        if len(all_issues) == 0:
            logger.warning("No tickets found in this date range.")
            return False

        # 4. Flatten issues into rows for CSV
        parsed_data = []
        for issue in all_issues:
            fields = issue.get("fields", {})

            def get_field(field_name, sub_field="name"):
                val = fields.get(field_name)
                if isinstance(val, dict):
                    return val.get(sub_field, "")
                return val if val else ""

            row = {
                "Issue Key": issue.get("key"),
                "Issue Type": get_field("issuetype"),
                "Updated": fields.get("updated"),
                "Status": get_field("status"),
                "Resolved": fields.get("resolutiondate"),
                "Project Name": get_field("project"),
                "Summary": fields.get("summary"),
                "Assignee": get_field("assignee", "displayName"),
                "Priority": get_field("priority"),
                "Created": fields.get("created"),
                "Platform": get_field("customfield_12345"),
                "Worklog": fields.get("worklog", {}).get("total") if fields.get("worklog") else 0,
            }
            parsed_data.append(row)

        # 5. Save to CSV
        df = pd.DataFrame(parsed_data)
        df.to_csv(output_csv_path, index=False)
        logger.info(f"Saved Jira dump to {output_csv_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch from Jira: {str(e)}")
        raise e