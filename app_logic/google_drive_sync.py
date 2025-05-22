import os
import pickle
import logging # Import logging module
import io

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError, GoogleAuthError
from googleapiclient.errors import HttpError # For Google API errors
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# --- Setup Logging ---
# Configure basic logging. In a larger app, this might be in a central config.
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("notes_app.log"), logging.StreamHandler()]) # Log to file and console
logger = logging.getLogger(__name__) # Get a logger for this module


# Define the scope for the Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.appdata']
TOKEN_PICKLE_PATH = 'token.pickle' # Path to store/load token
CREDENTIALS_JSON_PATH = 'credentials.json' # Path to the OAuth 2.0 credentials file

# --- Application Folder Management ---
APP_DATA_FOLDER_ID = 'appDataFolder' # Special identifier for the appDataFolder

def get_or_create_app_folder(service):
    """
    Verifies access to the 'appDataFolder'.

    Args:
        service: Authenticated Google Drive API service object.

    Returns:
        str: The ID of the app folder ('appDataFolder') if accessible, else None.
    """
    if not service:
        logger.error("get_or_create_app_folder: Google Drive service object is None.")
        return None
    try:
        # Test access by listing (can be any lightweight operation)
        service.files().list(spaces=APP_DATA_FOLDER_ID, pageSize=1, fields="files(id)").execute()
        logger.info(f"Successfully accessed Google Drive '{APP_DATA_FOLDER_ID}'.")
        return APP_DATA_FOLDER_ID
    except HttpError as e:
        logger.error(f"Google API HTTP error while accessing '{APP_DATA_FOLDER_ID}': {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
        if e.resp and e.resp.get('content-type', '').startswith('application/json'):
            logger.error(f"API Error details: {e.content}")
        return None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error accessing '{APP_DATA_FOLDER_ID}': {e}", exc_info=True)
        return None


def authenticate_google_drive():
    """
    Handles OAuth 2.0 authentication for Google Drive API.
    Returns an authenticated Google Drive API service object or None if authentication fails.
    """
    creds = None
    if os.path.exists(TOKEN_PICKLE_PATH):
        try:
            with open(TOKEN_PICKLE_PATH, 'rb') as token_file:
                creds = pickle.load(token_file)
            logger.info("Token loaded successfully from token.pickle.")
        except (pickle.UnpicklingError, EOFError, IOError) as e: # More specific exceptions for token loading
            logger.error(f"Error loading token from '{TOKEN_PICKLE_PATH}': {e}. Will attempt re-authentication.", exc_info=True)
            creds = None
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"Unexpected error loading token: {e}. Will attempt re-authentication.", exc_info=True)
            creds = None


    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Credentials expired. Attempting to refresh token...")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully.")
            except RefreshError as e:
                logger.error(f"Error refreshing token: {e}. User will need to re-authorize.", exc_info=True)
                creds = None
            except GoogleAuthError as e: # Catch broader auth errors
                logger.error(f"Google Auth error refreshing token: {e}. User will need to re-authorize.", exc_info=True)
                creds = None
            except Exception as e: # Catch other potential errors during refresh
                logger.error(f"Unexpected error refreshing token: {e}. User will need to re-authorize.", exc_info=True)
                creds = None
        
        if not creds: # If still no creds (initial auth or refresh failed)
            logger.info("No valid credentials. Initiating new authentication flow.")
            if not os.path.exists(CREDENTIALS_JSON_PATH):
                logger.error(f"CRITICAL: OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found. Download from Google Cloud Console.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_JSON_PATH, SCOPES)
                creds = flow.run_local_server(prompt='consent', open_browser=True)
                logger.info("User authenticated successfully through browser flow.")
            except FileNotFoundError: # Should be caught by os.path.exists, but good to be defensive
                logger.error(f"CRITICAL: OAuth credentials file '{CREDENTIALS_JSON_PATH}' not found during flow initiation.", exc_info=True)
                return None
            except GoogleAuthError as e: # Catch broader auth errors during flow
                logger.error(f"Google Auth error during authentication flow: {e}", exc_info=True)
                return None
            except Exception as e: # Catch other errors like server binding issues etc.
                logger.error(f"Authentication flow failed: {e}", exc_info=True)
                return None

        if creds:
            try:
                with open(TOKEN_PICKLE_PATH, 'wb') as token_file:
                    pickle.dump(creds, token_file)
                logger.info(f"Credentials saved successfully to '{TOKEN_PICKLE_PATH}'.")
            except IOError as e: # More specific error for saving token
                logger.error(f"Error saving token to '{TOKEN_PICKLE_PATH}': {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error saving token: {e}", exc_info=True)
    
    if creds and creds.valid:
        try:
            service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive API service built successfully.")
            return service
        except HttpError as e: # Catch HttpError during service build specifically
            logger.error(f"Google API HTTP error building Drive service: {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Failed to build Google Drive service: {e}", exc_info=True)
            return None
    else:
        logger.warning("Authentication ultimately failed or was cancelled by the user.")
        return None

if __name__ == '__main__':
    # This is for testing the authentication flow directly.
    # In a real application, this would be called by main.py or another module.
    print("Attempting to authenticate with Google Drive...")
    drive_service = authenticate_google_drive()
    if drive_service:
        print("Authentication successful! Service object created.")
        # Test appDataFolder access
        folder_id_to_use = get_or_create_app_folder(drive_service)
        if folder_id_to_use:
            print(f"App folder ID to use: {folder_id_to_use}")
            # Further testing with list_files could be added here if desired
            # For example:
            # remote_files = list_files_in_app_folder(drive_service, folder_id_to_use)
            # print(f"Files in app folder: {remote_files}")
    else:
        print("Authentication failed.")


# --- File Operations ---

def list_files_in_app_folder(service, folder_id):
    """
    Lists all files within the given folder_id (typically 'appDataFolder').

    Args:
        service: Authenticated Google Drive API service object.
        folder_id: The ID of the folder to list files from.

    Returns:
        dict: Mapping of file names to their Google Drive file IDs.
              Returns an empty dict if an error occurs or no files are found.
    """
    if not service:
        logger.error("list_files_in_app_folder: Google Drive service object is None.")
        return {}
    if not folder_id:
        logger.error("Error: No folder_id provided to list_files_in_app_folder.")
        return {}
    
    files_map = {}
    try:
        # For appDataFolder, 'spaces' is used. For other folders, 'q' with 'parents in' is used.
        query_params = {
            'fields': "nextPageToken, files(id, name)",
            'pageSize': 100 # Adjust as needed
        }
        if folder_id == APP_DATA_FOLDER_ID:
            query_params['spaces'] = APP_DATA_FOLDER_ID
        else:
            query_params['q'] = f"'{folder_id}' in parents and trashed=false" # Exclude trashed files

        results = service.files().list(**query_params).execute()
        
        items = results.get('files', [])
        for item in items:
            # Assuming note titles are file names without .txt extension for consistency
            # However, Drive files can have any name. We store them as is.
            # The sync logic should handle if .txt is part of the name on Drive or not.
            # For now, store the name as is from Drive.
            files_map[item['name']] = item['id'] 
        logger.info(f"Found {len(files_map)} files in Drive folder '{folder_id}'.")
    except HttpError as e:
        logger.error(f"Google API HTTP error listing files in folder '{folder_id}': {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
        return {}
    except Exception as e:
        logger.error(f"Unexpected error listing files in folder '{folder_id}': {e}", exc_info=True)
        return {}
    return files_map

def upload_note(service, folder_id, local_filepath, note_title_on_drive, existing_file_id=None):
    """
    Uploads or updates a note to Google Drive.
    Args:
        note_title_on_drive: The name the file should have on Google Drive.
    Returns:
        str: The ID of the uploaded/updated file, or None on failure.
    """
    if not service:
        logger.error("upload_note: Google Drive service object is None.")
        return None
    if not folder_id:
        logger.error("Error: No folder_id provided for upload.")
        return None
    if not os.path.exists(local_filepath):
        logger.error(f"Error: Local file '{local_filepath}' not found for upload.")
        return None

    file_metadata = {'name': note_title_on_drive}
    # Parent folder assignment differs for appDataFolder vs regular folders
    if folder_id != APP_DATA_FOLDER_ID:
        file_metadata['parents'] = [folder_id]
    else:
        # For appDataFolder, 'parents' should be ['appDataFolder'] or handled by the scope.
        # Explicitly setting it seems more robust with V3 API.
        file_metadata['parents'] = [APP_DATA_FOLDER_ID] 
    
    try:
        media = MediaFileUpload(local_filepath, mimetype='text/plain', resumable=True)
    except Exception as e: # Catch error if local_filepath is invalid for MediaFileUpload
        logger.error(f"Error creating MediaFileUpload for '{local_filepath}': {e}", exc_info=True)
        return None

    try:
        if existing_file_id:
            logger.info(f"Updating existing Drive file ID '{existing_file_id}' with content from '{local_filepath}' as '{note_title_on_drive}'.")
            # Note: If renaming, file_metadata should be passed in body. If only content, body can be omitted.
            # To update metadata (like name) and content:
            updated_file = service.files().update(
                fileId=existing_file_id,
                body=file_metadata, # Pass new metadata (e.g., if name changes)
                media_body=media,
                fields='id, name'
            ).execute()
            logger.info(f"Note '{updated_file.get('name')}' (ID: {updated_file.get('id')}) updated successfully in Drive.")
            return updated_file.get('id')
        else:
            logger.info(f"Uploading new note '{note_title_on_drive}' from '{local_filepath}' to Drive folder '{folder_id}'.")
            # For create, file_metadata (which includes parents) is in body.
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name' # Request 'name' field back to log it
            ).execute()
            logger.info(f"Note '{created_file.get('name')}' (ID: {created_file.get('id')}) uploaded successfully to Drive folder '{folder_id}'.")
            return created_file.get('id')
    except HttpError as e:
        logger.error(f"Google API HTTP error uploading/updating note '{note_title_on_drive}': {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
        if e.resp and e.resp.get('content-type', '').startswith('application/json'):
            logger.error(f"API Error details: {e.content}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error uploading/updating note '{note_title_on_drive}': {e}", exc_info=True)
        return None


def download_note(service, file_id, local_filepath):
    """
    Downloads a note from Google Drive. Returns True on success, False otherwise.
    """
    if not service:
        logger.error("download_note: Google Drive service object is None.")
        return False
    logger.info(f"Attempting to download Drive file ID '{file_id}' to '{local_filepath}'.")
    try:
        request = service.files().get_media(fileId=file_id)
        # Ensure parent directory for local_filepath exists
        local_dir = os.path.dirname(local_filepath)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir) # Create directory if it doesn't exist
            logger.info(f"Created local directory '{local_dir}' for download.")

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status: logger.debug(f"Download for {file_id}: {int(status.progress() * 100)}%.")
        
        fh.seek(0)
        with open(local_filepath, 'wb') as f:
            f.write(fh.read())
        logger.info(f"Note ID '{file_id}' downloaded successfully to '{local_filepath}'.")
        return True
    except HttpError as e:
        logger.error(f"Google API HTTP error downloading note ID '{file_id}': {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
        return False
    except IOError as e: # Catch errors writing file locally
        logger.error(f"IOError saving downloaded note to '{local_filepath}': {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading note ID '{file_id}': {e}", exc_info=True)
        return False

def delete_note_from_drive(service, file_id):
    """
    Deletes a note from Google Drive. Returns True on success, False otherwise.
    """
    if not service:
        logger.error("delete_note_from_drive: Google Drive service object is None.")
        return False
    logger.info(f"Attempting to delete Drive file ID '{file_id}'.")
    try:
        service.files().delete(fileId=file_id).execute()
        logger.info(f"Note ID '{file_id}' deleted successfully from Drive.")
        return True
    except HttpError as e:
        logger.error(f"Google API HTTP error deleting note ID '{file_id}': {e.status_code} - {e.resp.get('reason', str(e))}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting note ID '{file_id}' from Drive: {e}", exc_info=True)
        return False

# --- Synchronization Logic ---

def synchronize_notes(service, local_notes_dir="notes", drive_folder_id_to_use=None):
    """
    Synchronizes notes between local directory and Google Drive.
    Returns:
        bool: True if entire sync process seems successful, False if any part fails.
    """
    overall_success = True # Track if all operations succeed

    if not service:
        logger.error("Synchronization failed: Google Drive service not available.")
        return False # Critical failure

    if not drive_folder_id_to_use:
        logger.info("Drive folder ID not provided, attempting to determine using get_or_create_app_folder...")
        drive_folder_id_to_use = get_or_create_app_folder(service)
        if not drive_folder_id_to_use:
            logger.error("Synchronization failed: Could not determine Google Drive folder ID.")
            return False # Critical failure
    
    logger.info(f"Starting synchronization: Local='{local_notes_dir}', Drive Folder='{drive_folder_id_to_use}'")

    # 1. Get local notes (title -> full_path)
    local_notes = {} 
    if not os.path.exists(local_notes_dir):
        try:
            os.makedirs(local_notes_dir)
            logger.info(f"Created local notes directory: {local_notes_dir}")
        except OSError as e:
            logger.error(f"Failed to create local notes directory '{local_notes_dir}': {e}", exc_info=True)
            return False # Critical failure

    try:
        for filename in os.listdir(local_notes_dir):
            if filename.endswith(".txt"):
                local_notes[filename[:-4]] = os.path.join(local_notes_dir, filename) # Key is note title without .txt
    except OSError as e:
        logger.error(f"Error listing local notes in '{local_notes_dir}': {e}", exc_info=True)
        return False # Critical failure
    logger.info(f"Local notes found: {list(local_notes.keys())}")

    # 2. Get remote notes (name_on_drive -> id)
    # Note: remote_notes keys are actual filenames on Drive (e.g., "My Note.txt" or "My Note")
    remote_notes_map = list_files_in_app_folder(service, drive_folder_id_to_use)
    if remote_notes_map is None: # list_files_in_app_folder returns {} on error, could return None for critical failure
        logger.error("Synchronization failed: Could not list remote files.")
        return False
    logger.info(f"Remote notes found (name_on_drive -> id): {remote_notes_map}")


    # 3. Compare and Sync
    # Strategy: local note titles are without .txt. Drive filenames may or may not have .txt.
    # We'll assume local title should map to Drive filename "title.txt".

    # Local to Drive:
    for local_title, local_path in local_notes.items():
        drive_filename_expected = f"{local_title}.txt" # Assume .txt extension on Drive for comparison
        if drive_filename_expected not in remote_notes_map:
            logger.info(f"Local note '{local_title}' (expected as '{drive_filename_expected}' on Drive) not found on Drive. Uploading...")
            if not upload_note(service, drive_folder_id_to_use, local_path, drive_filename_expected):
                logger.warning(f"Failed to upload local note '{local_title}' to Drive.")
                overall_success = False 
        # else: Note exists on Drive (by expected name).
            # TODO: Implement modification date check for updates.
            # For now, if it exists by name, we assume it's synced or handle conflict manually.
            # Example for update:
            # drive_file_id = remote_notes_map[drive_filename_expected]
            # # Check modification times, then:
            # # upload_note(service, drive_folder_id_to_use, local_path, drive_filename_expected, existing_file_id=drive_file_id)


    # Drive to Local:
    for drive_filename, file_id in remote_notes_map.items():
        # Derive a potential local title from the Drive filename
        # If Drive filename is "My Note.txt", local title is "My Note"
        # If Drive filename is "My Other Note" (no .txt), local title is "My Other Note"
        local_title_derived = drive_filename[:-4] if drive_filename.endswith(".txt") else drive_filename
        
        if local_title_derived not in local_notes:
            logger.info(f"Remote note '{drive_filename}' (ID: {file_id}) not found locally as '{local_title_derived}'. Downloading...")
            local_filepath_to_save = os.path.join(local_notes_dir, f"{local_title_derived}.txt") # Always save with .txt locally
            if not download_note(service, file_id, local_filepath_to_save):
                logger.warning(f"Failed to download remote note '{drive_filename}' (ID: {file_id}).")
                overall_success = False
        # else: Note exists locally (by derived title).
            # TODO: Implement modification date check for updates.

    if overall_success:
        logger.info("Synchronization process completed successfully.")
    else:
        logger.warning("Synchronization process completed with some errors. Check logs.")
    return overall_success


# Example usage (for testing, would be called from main.py or similar)
if __name__ == '__main__':
    logger.info("--- Starting Google Drive Sync Module Test ---")
    drive_service_instance = authenticate_google_drive()
    
    if drive_service_instance:
        logger.info("Authentication successful. Proceeding with sync test.")
        
        app_folder_identifier = get_or_create_app_folder(drive_service_instance)
        
        if app_folder_identifier:
            logger.info(f"Using Drive folder: {app_folder_identifier}")
            
            # Create a temporary local directory for this test
            test_local_dir = "notes_sync_test_temp"
            if not os.path.exists(test_local_dir):
                os.makedirs(test_local_dir)
            
            # Create some dummy local notes for testing
            with open(os.path.join(test_local_dir, "Local Note Alpha.txt"), "w") as f:
                f.write("Content of Local Note Alpha.")
            with open(os.path.join(test_local_dir, "Common Note Beta.txt"), "w") as f:
                f.write("Local version of Common Note Beta.")

            logger.info(f"\n--- Initiating Sync Test (Local Dir: '{test_local_dir}') ---")
            sync_status = synchronize_notes(drive_service_instance, 
                                            local_notes_dir=test_local_dir, 
                                            drive_folder_id_to_use=app_folder_identifier)
            logger.info(f"--- Sync Test Ended (Success: {sync_status}) ---\n")

            logger.info("--- Post-Sync Verification ---")
            logger.info("Listing remote files in appDataFolder post-sync:")
            all_remote_files = list_files_in_app_folder(drive_service_instance, app_folder_identifier)
            for name, id_ in all_remote_files.items():
                logger.info(f" - Remote: {name} (ID: {id_})")
            
            logger.info("\nListing local files post-sync in '{test_local_dir}':")
            if os.path.exists(test_local_dir):
                for f_name in os.listdir(test_local_dir):
                    logger.info(f" - Local: {f_name}")
            
            # Clean up dummy local directory (optional)
            # import shutil
            # shutil.rmtree(test_local_dir)
            # logger.info(f"Cleaned up test directory: {test_local_dir}")
        else:
            logger.error("Could not get/create app folder, sync test aborted.")
    else:
        logger.error("Authentication failed, sync test aborted.")
    
    logger.info("--- Google Drive Sync Module Test Ended ---")
