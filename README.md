# dropbox-directory

Scripts to create a directory of Virulent Hate's Dropbox team folder with sharable links.

**Author:** Jake Gibson, Virulent Hate Project Manager

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
    1. Go to the [Dropbox Developers site](https://www.dropbox.com/developers/apps), create an app, and [generate a personal Access Token](https://dropbox.tech/developers/generate-an-access-token-for-your-own-account). Replace the `DROPBOX_ACCESS_TOKEN` variable in the `.env` file.
5. Execute the desired script using the newly created virtual environment as the interpreter.