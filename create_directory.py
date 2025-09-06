import os
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


def get_folder_contents(folder_id):
    items = []
    page_token = None
    while True:
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


def traverse_and_create(folder_id, parent_path, metadata_rows):
    contents = get_folder_contents(folder_id)
    for item in contents:
        # Create a directory for every item (file or folder)
        item_path = os.path.join(parent_path, item["name"])
        item["path"] = item_path
        metadata_rows.append(item)
        if item.get("is_folder", False):
            # Recursively process subfolders
            traverse_and_create(item["id"], item_path, metadata_rows)


def write_csv(metadata_rows, csv_file_path):
    if not metadata_rows:
        return
    fieldnames = [
        "name",
        "path",
        "id",
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
    traverse_and_create(root_folder_id, root_folder_name, metadata_rows)
    write_csv(metadata_rows, csv_path)
    print(
        f"Process complete. Directory structure at {root_folder_name}, metadata saved to {csv_path}."
    )
