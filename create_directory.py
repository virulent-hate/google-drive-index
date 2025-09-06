import os
import time
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import csv

# Google Drive API settings
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]
SERVICE_ACCOUNT_FILE = "credentials.json"

# Authenticate with Google API and build the service
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
service = build("drive", "v3", credentials=creds)


def exponential_backoff_sleep(retry_count):
    # Exponential backoff with jitter (see Google best practices)
    # e.g., sleep random time between 0 and 2^retry_count seconds (max 64 seconds)
    max_sleep = min(2**retry_count, 64)
    sleep_time = random.uniform(0, max_sleep)
    print(f"Rate limited. Sleeping for {sleep_time:.2f} seconds before retry...")
    time.sleep(sleep_time)


def get_folder_contents(folder_id, max_retries=7):
    items = []
    page_token = None
    while True:
        for attempt in range(max_retries):
            try:
                results = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        pageSize=1000,
                        fields="nextPageToken, files(id, name, mimeType, size, owners, createdTime, modifiedTime)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                break  # Success, exit retry loop
            except HttpError as e:
                if e.resp.status == 429:
                    exponential_backoff_sleep(attempt)
                    continue  # Retry after backoff
                else:
                    print(f"Unhandled HttpError: {e}")
                    raise  # Reraise other errors
        else:
            # We exhausted retries
            raise RuntimeError(
                f"Exceeded maximum retries for folder {folder_id} (rate limit)."
            )

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
        page_token = results.get("nextPageToken", None)
        if not page_token:
            break
    return items


def create_share_link(item):
    if item["is_folder"]:
        link = f"https://drive.google.com/drive/folders/{item['id']}?usp=drivesdk"
    else:
        link = f"https://drive.google.com/file/d/{item['id']}?usp=drivesdk"
    return link


def traverse_and_create(folder_id, parent_path, metadata_rows):
    contents = get_folder_contents(folder_id)
    for item in contents:
        item_path = os.path.join(parent_path, item["name"])
        item["path"] = item_path
        item["link"] = create_share_link(item)
        metadata_rows.append(item)
        if item.get("is_folder", False):
            traverse_and_create(item["id"], item_path, metadata_rows)


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


if __name__ == "__main__":
    # Set folder id and name for directory
    root_folder_id = "1k-_alN-wNT1nSiMPXFdR5MHLmyHEhHUC"
    root_folder_name = "NewsBank_2021-01-24_2021-01-30"

    # Establish CSV path, call traversal function, and create CSV
    csv_path = os.path.join("directories", f"{root_folder_name}_directory.csv")
    metadata_rows = []
    print("Processing Google Drive structure. This may take a while for large trees...")
    try:
        traverse_and_create(root_folder_id, root_folder_name, metadata_rows)
        write_csv(metadata_rows, csv_path)
    except Exception as e:
        print(f"Aborted due to error: {e}")
    else:
        print(
            f"Process complete. Directory structure at {root_folder_name}, metadata saved to {csv_path}."
        )
