import os
import time
import random
import csv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv(override=True)

# Google Drive API settings
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]
SERVICE_ACCOUNT_FILE = "credentials.json"

# Authenticate with Google API and build the service
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build("drive", "v3", credentials=creds)


def exponential_backoff_sleep(retry_count):
    """
    Exponential backoff function with jitter. Sleeps a random time between 0 and 2^retry_count seconds (max 64 seconds). Function is called if per-minute Google API call limits are reached.

    parameters:
      - retry_count (int): number of failed attempts at API calls. Sleep time increase with number of attempts (until 64 seconds).
    """
    max_sleep = min(2**retry_count, 64)
    sleep_time = random.uniform(0, max_sleep)
    print(f"Rate limited. Sleeping for {sleep_time:.2f} seconds before retry...")
    time.sleep(sleep_time)


def get_folder_metadata(folder_id, max_retries=7):
    """
    Lists all items in Google Drive folder.

    parameters:
      - folder_id (str): ID of Google Drive folder for creating index.
      -max_retries (int; default 7): max number of retries after failed API calls.

    returns:
      - items (list): list of item dictionaries containing metadata for each file and folder in root.
    """
    # Initialize empty variables
    items = []
    page_token = None

    # Call Google Drive API and list files and folders within root folder
    while True:
        for attempt in range(max_retries):
            try:
                call = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    pageSize=1000,
                    fields="nextPageToken, files(id, name, mimeType, size, owners, webViewLink, createdTime, modifiedTime)",
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                results = call.execute()
                break
            except HttpError as e:
                if e.resp.status == 429:  # Error code for API rate limit
                    exponential_backoff_sleep(attempt)
                    continue
                else:
                    print(f"Unhandled HttpError: {e}")
                    raise
        else:
            raise RuntimeError(
                f"Exceeded maximum retries for folder {folder_id} (rate limit)."
            )

        # For each file, extract metadata, store in dictionary, and add to items list
        files = results.get("files", [])
        for f in files:
            is_folder = f["mimeType"] == "application/vnd.google-apps.folder"
            size = int(f["size"]) if "size" in f else 0
            size_kb = round(size / 1024, 2) if not is_folder else 0
            owner = f.get("owners", [{}])[0].get("displayName", "")
            # link = create_share_link(f["id"], is_folder)
            items.append(
                {
                    "id": f["id"],
                    "name": f["name"],
                    "link": f["webViewLink"],
                    "type": f["mimeType"],
                    "is_folder": is_folder,
                    "size_kb": size_kb,
                    "owner": owner,
                    "created_date": f.get("createdTime", ""),
                    "last_modified_date": f.get("modifiedTime", ""),
                }
            )
        # Page token indicates if more items in folder (on following page)
        page_token = results.get("nextPageToken", None)
        if not page_token:
            break

    return items


def traverse_folder(folder_id, parent_path, metadata_rows):
    """
    Calls get_folder_metadata function for root folder, appending file/folder metadata to metadata_rows. If additional folders are present, recursively calls traverse_folder until only files are contained in the directory.

    parameters:
      - folder_id (str): Google Drive folder id
      - parent_path (str): root folder name
      - metadata_rows (list): list for appending file/folder metadata
    """
    contents = get_folder_metadata(folder_id)
    for item in contents:
        item_path = os.path.join(parent_path, item["name"])  # Create path for folder
        item["path"] = item_path
        metadata_rows.append(item)
        if item.get("is_folder", False):
            traverse_folder(item["id"], item_path, metadata_rows)


def write_csv(metadata_rows, csv_file_path):
    """
    Writes Google Drive metadata to CSV file.

    parameters:
        - metadata_rows (list): list of dictionaries with with metadata.
        - csv_file_path (os.path): path to csv output destination
    """
    if not metadata_rows:
        return
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)
    fieldnames = [
        "name",
        "path",
        "id",
        "link",
        "type",
        "is_folder",
        "size_kb",
        "owner",
        "created_date",
        "last_modified_date",
    ]
    with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metadata_rows)


if __name__ == "__main__":
    # Import and initialize variables
    root_folder_id = os.getenv("ROOT_FOLDER_ID")  # adjust in .env file
    root_folder_name = os.getenv("ROOT_FOLDER_NAME")  # adjust in .env file
    csv_path = os.path.join("indexes", f"{root_folder_name}_index.csv")
    metadata_rows = []

    print(
        f"\nProcessing files in Google Drive folder. This may take a while for large trees...\n"
    )

    try:
        traverse_folder(root_folder_id, root_folder_name, metadata_rows)
        write_csv(metadata_rows, csv_path)
    except Exception as e:
        print(f"\nAborted due to error: {e}\n")
    else:
        print(f"\nProcess complete. Index of files {root_folder_name} to {csv_path}.\n")
