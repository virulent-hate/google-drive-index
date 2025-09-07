# google-drive-index

Python script creating an index of files and folders in a Google Drive directory using the Google Drive API.

**Author:** Jake Gibson, [Virulent Hate](https://virulenthate.org/) Project Manager

**Institution:** University of Michigan

**Date:** September 2025

**Contact:** jacobgib@umich.edu

## Development Information
- **Python Version:** 3.13.2
- **Dependency tracking**
    - `requirements.in`: List of primary dependencies.
    - `requirements.txt`: Full list of dependencies compiled using pip-tools.

## Executing this Repository
1. Clone this repository.
2. Create a new virtual environment using Python 3.13.2.
3. Install the required packages listed in the `requirements.txt` file found in the repository's root directory.
4. Duplicate the example environment file `.env.example` and **rename it `.env`**.
5. Follow instructions from [Google Drive API Python quickstart](https://developers.google.com/workspace/drive/api/quickstart/python).
    1. Create Google Cloud Project and enable [Google Drive API](https://console.cloud.google.com/flows/enableapi?apiid=drive.googleapis.com).
    2. Configure [OAuth consent](https://console.cloud.google.com/auth/branding).
    3. Create [client credentials](https://console.cloud.google.com/auth/clients), downloading as `credentias.json`.
    4. Run `quickstart.py` (included in this repository) to authenticate device (authentication saved as `token.json`).
6. Adjust variables in `.env` file to desired Google Drive folder.
    - The Google Drive folder ID is embedded in the sharable link. In the URL, the ID is the long string characters after "folders/".
    - Link: `https://drive.google.com/drive/folders/1nLfEtbSrX4zS2OkcuZeOJovKs-GGWkYv`
    - ID: `1nLfEtbSrX4zS2OkcuZeOJovKs-GGWkYv`
7. Execute `create_index.py` using the newly created virtual environment as the interpreter.
    1. Indexes will be saved for a `indexes/` directory (which is included in the `.gitignore` file to prevent metadata from being exposed to GitHub)
