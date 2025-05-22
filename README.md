# Simple Notes with Drive Sync

## Overview

Simple Notes with Drive Sync is a desktop note-taking application built with Python and Tkinter. It allows users to create, edit, save, and delete notes locally. Additionally, it features integration with Google Drive for backing up and synchronizing notes to your personal Google Drive account, stored in a special application-specific folder.

## Features

*   **Local Note Management:** Create, edit, save, and delete notes on your computer.
*   **Google Drive Synchronization:**
    *   Authenticate with your Google Account to back up notes to Google Drive.
    *   Synchronize notes between your local storage and Google Drive.
*   **User Interface:** A basic graphical user interface built using Python's Tkinter library.
*   **Cross-Platform:** Being Python-based, it can run on Windows, macOS, and Linux (with Python and Tkinter installed).

## Requirements

*   **Python 3.x** (Python 3.6 or newer recommended)
*   **Dependencies:**
    *   `google-api-python-client`
    *   `google-auth-oauthlib`

    You can install these dependencies using pip:
    ```bash
    pip install google-api-python-client google-auth-oauthlib
    ```
    (Consider creating a `requirements.txt` file with these packages for easier installation: `pip install -r requirements.txt`)

## Setup and Configuration

### 1. Google Drive API Credentials (`credentials.json`)

To use the Google Drive synchronization feature, you need to obtain OAuth 2.0 client credentials from the Google Cloud Console.

**Steps to get `credentials.json`:**

1.  **Go to Google Cloud Console:** Visit [https://console.cloud.google.com/](https://console.cloud.google.com/).
2.  **Create or Select a Project:**
    *   If you don't have a project, click on the project selector, then "NEW PROJECT". Give it a name (e.g., "MyNotesAppProject") and create it.
    *   If you have an existing project, select it.
3.  **Enable the Google Drive API:**
    *   In the navigation menu (☰), go to "APIs & Services" > "Library".
    *   Search for "Google Drive API" and select it.
    *   Click the "Enable" button.
4.  **Create OAuth Client ID Credentials:**
    *   In the navigation menu, go to "APIs & Services" > "Credentials".
    *   Click on "+ CREATE CREDENTIALS" at the top and select "OAuth client ID".
    *   **Configure OAuth Consent Screen (if prompted):**
        *   Choose "External" user type.
        *   Fill in the required fields: App name (e.g., "SimpleNotesApp"), User support email, and Developer contact information.
        *   Click "SAVE AND CONTINUE" through Scopes and Test users (you don't need to add specific scopes or test users here for this app type).
        *   Once the consent screen is configured, navigate back to "Credentials". Click "+ CREATE CREDENTIALS" > "OAuth client ID" again.
    *   **Application Type:** Select "Desktop app" from the dropdown menu.
    *   **Name:** Give your OAuth client ID a name (e.g., "MyNotesAppDesktopClient").
    *   Click "CREATE".
5.  **Download and Rename Credentials:**
    *   A dialog will appear showing your Client ID and Client Secret. Click "DOWNLOAD JSON" on the right.
    *   Save the downloaded file.
    *   **Rename the downloaded file to `credentials.json` and place it in the root directory of this application.**

**IMPORTANT:** The `credentials.json` file contains sensitive information. Keep it secure and do not share it or commit it to public version control repositories.

### 2. Local Notes Directory

Your local notes are stored as `.txt` files in a directory named `notes/` which will be created automatically in the application's root directory when you first save a note.

## How to Run

1.  Ensure you have Python 3.x and the required dependencies installed (see "Requirements").
2.  Make sure the `credentials.json` file is correctly set up in the root directory of the application.
3.  Open a terminal or command prompt, navigate to the application's root directory, and run:

    ```bash
    python main.py
    ```

## Google Drive Synchronization - Current Behavior & Limitations

The application uses Google Drive to store a copy of your notes. This allows you to have a backup and potentially access them from different instances of this application if configured with the same Google Account.

*   **Storage Location (`appDataFolder`):** Notes are synced to a special, hidden folder in your Google Drive called the "Application Data folder" (`appDataFolder`). This folder is only accessible by this specific application instance (identified by your `credentials.json`). You won't see these files directly in your main Google Drive folders unless you use tools like Google Takeout or manage Drive API data.

*   **Authentication:**
    *   **First Run:** When you start the application for the first time (or after deleting `token.pickle`), it will attempt to authenticate with Google Drive. Your web browser will open, prompting you to log in to your Google Account and grant the application permission to access its `appDataFolder`.
    *   **Subsequent Runs:** After successful authentication, an authorization token is stored locally in a file named `token.pickle`. Future launches will use this token to automatically authenticate. If the token expires or is revoked, the application will attempt to refresh it or re-prompt for authentication.

*   **Sync Logic (Manual Trigger):**
    *   Synchronization is **triggered manually** by clicking the "Sync with Google Drive" button in the application.

    *   **New Notes:**
        *   If a note exists locally but not on Drive (matched by title, assuming `.txt` extension on Drive), it will be uploaded to Drive.
        *   If a note exists on Drive (in the `appDataFolder`) but not locally, it will be downloaded to your local `notes/` directory.

    *   **Updates to Existing Notes: IMPORTANT LIMITATION**
        *   If a note with the same title exists both locally and on Drive, its content **WILL NOT be updated or merged** by the current sync process. The application does not compare modification times or content for notes that already exist in both locations by the same name. This means if you edit a note locally and the same titled note exists on Drive, your local changes **will not** be uploaded to overwrite the Drive version, and vice-versa.

    *   **Deletions: IMPORTANT LIMITATION**
        *   Deleting a note locally **DOES NOT delete it from Google Drive**. On the next sync, the application will see the note on Drive but not locally, and it will be **re-downloaded**.
        *   Deleting a note directly from the `appDataFolder` on Google Drive (e.g., via API tools, as it's not typically user-visible) **DOES NOT delete it locally**. On the next sync, the application will see the note locally but not on Drive, and it will be **re-uploaded**.

    *   **In summary:** The current synchronization feature is best thought of as a way to:
        1.  Get new local notes backed up to Drive.
        2.  Retrieve new notes from Drive that aren't local yet.
        It is **not a full mirror sync** for updates to existing notes or for propagating deletions.

## Logging

The application maintains a log file for diagnostic purposes, especially for Google Drive operations.
*   **Log File:** `notes_app.log` (located in the root directory).
*   This file can be helpful for troubleshooting issues with authentication or synchronization.

## Future Improvements (Potential)

*   **Advanced Sync Logic:**
    *   Implement proper handling of updates to existing notes (e.g., using modification timestamps or content hashing to sync the latest version).
    *   Propagate deletions correctly between local and Drive.
*   **Conflict Resolution:** If a note is edited in both places independently, provide a mechanism for the user to resolve the conflict.
*   **Automatic Background Synchronization:** Option for the app to sync automatically at intervals or on change.
*   **More Robust Error Handling:** Even more detailed user feedback for specific Drive API errors.
*   **UI Enhancements:** Rich text editing, note organization (folders/tags), search functionality.
*   **Packaging:** Create distributable executables for different operating systems.

---

We hope you find this Simple Notes application useful!
