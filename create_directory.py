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


def get_folder_contents(folder_id, shared_drive_id=None, max_retries=7):
    """
    Lists all items in Google Drive folder.

    parameters:
      - folder_id (str): ID of Google Drive folder for creating directory
      - shared_drive_id (str): if folder is located in Google Shared Drive, the ID of that drive must be provided.
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
                    fields="nextPageToken, files(id, name, mimeType, size, owners, createdTime, modifiedTime)",
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
            items.append(
                {
                    "id": f["id"],
                    "name": f["name"],
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


def create_share_link(item):
    """
    Creates a shareable link to each file or folder using Google Drive's standard link format.

    parameters:
      - item (dict): item containing (at minimum) "is_folder" (bool) and a Google Drive ID.

    returns:
      - link (str): URL for Google Drive file/folder
    """
    if item["is_folder"]:
        link = f"https://drive.google.com/drive/folders/{item['id']}?usp=drivesdk"
    else:
        link = f"https://drive.google.com/file/d/{item['id']}?usp=drivesdk"
    return link


def get_metadata(folder_id, parent_path, metadata_rows, shared_drive_id=None):
    """
    Top-level function, calling on get_folder_contents to get
    """
    contents = get_folder_contents(folder_id, shared_drive_id=shared_drive_id)
    for item in contents:
        item_path = os.path.join(parent_path, item["name"])
        item["path"] = item_path
        item["link"] = create_share_link(item)
        metadata_rows.append(item)
        if item.get("is_folder", False):
            get_metadata(
                item["id"], item_path, metadata_rows, shared_drive_id=shared_drive_id
            )


def write_csv(metadata_rows, csv_file_path):
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


def get_shared_drive_id(file_id):
    file = (
        service.files()
        .get(fileId=file_id, fields="id, name, driveId", supportsAllDrives=True)
        .execute()
    )

    return file.get("driveId")


if __name__ == "__main__":
    # Set folder id and name for directory
    root_folder_id = os.getenv("ROOT_FOLDER_ID")
    root_folder_name = os.getenv("ROOT_FOLDER_NAME")
    root_drive_id = get_shared_drive_id(root_folder_id)

    # Establish CSV path, call traversal function, and create CSV
    csv_path = os.path.join("directories", f"{root_folder_name}_directory.csv")
    metadata_rows = []
    print("Processing Google Drive structure. This may take a while for large trees...")
    try:
        get_metadata(root_folder_id, root_folder_name, metadata_rows, root_drive_id)
        write_csv(metadata_rows, csv_path)
    except Exception as e:
        print(f"Aborted due to error: {e}")
    else:
        print(
            f"Process complete. Directory structure at {root_folder_name}, metadata saved to {csv_path}."
        )
