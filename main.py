import tkinter as tk
from tkinter import simpledialog, messagebox
import os
from app_logic.google_drive_sync import authenticate_google_drive, synchronize_notes, get_or_create_app_folder

LOCAL_NOTES_DIR = "notes" # Define this constant for the local notes directory

class NoteTakingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Note-Taking Application")
        self.drive_service = None # To store the authenticated Google Drive service

        # Configure main window to be resizable
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=3) # Text area gets more space
        self.root.rowconfigure(0, weight=1)

        # PanedWindow for resizable listbox and text_area
        paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_window.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)

        # UI Elements
        self.listbox = tk.Listbox(paned_window, width=30, height=20) # Increased height
        # self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        paned_window.add(self.listbox, stretch="first")
        self.listbox.bind('<<ListboxSelect>>', self.display_note_content)

        self.text_area = tk.Text(paned_window, wrap=tk.WORD, height=20) # Increased height
        # self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5), pady=5)
        paned_window.add(self.text_area, stretch="always")


        button_frame = tk.Frame(root)
        # button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        button_frame.grid(row=0, column=2, sticky="ns", padx=5, pady=5)


        new_button = tk.Button(button_frame, text="New Note", command=self.new_note)
        new_button.pack(pady=5, fill=tk.X)

        save_button = tk.Button(button_frame, text="Save Note", command=self.save_note)
        save_button.pack(pady=5, fill=tk.X)

        delete_button = tk.Button(button_frame, text="Delete Note", command=self.delete_note)
        delete_button.pack(pady=5, fill=tk.X)

        self.sync_button = tk.Button(button_frame, text="Sync with Google Drive", command=self.sync_with_drive)
        self.sync_button.pack(pady=5, fill=tk.X)
        
        # Status Label
        self.status_label = tk.Label(root, text="Welcome! Please create or select a note.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        # self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=(0,5))


        self.load_notes()
        self.attempt_google_drive_auth() # Attempt authentication at startup

    def attempt_google_drive_auth(self):
        self.set_status("Attempting Google Drive authentication...", busy=True)
        try:
            self.drive_service = authenticate_google_drive()
            if self.drive_service:
                self.set_status("Google Drive authenticated successfully.")
                if hasattr(self, 'sync_button'): self.sync_button.config(state=tk.NORMAL)
            else:
                self.set_status("Google Drive authentication failed. Sync disabled.")
                messagebox.showwarning("Google Drive Authentication Failed", 
                                     "Could not authenticate with Google Drive. Please check credentials.json and console output. Sync functionality will be disabled.")
                if hasattr(self, 'sync_button'): self.sync_button.config(state=tk.DISABLED)
        except Exception as e:
            self.drive_service = None
            self.set_status(f"Google Drive auth error. Sync disabled.")
            messagebox.showerror("Google Drive Authentication Error", 
                                 f"An error occurred during Google Drive authentication: {e}. Sync functionality will be disabled.")
            if hasattr(self, 'sync_button'): self.sync_button.config(state=tk.DISABLED)
        finally:
            self.set_busy_cursor(False)


    def set_status(self, message, busy=False):
        self.status_label.config(text=message)
        self.set_busy_cursor(busy)
        self.root.update_idletasks()

    def set_busy_cursor(self, busy_status):
        if busy_status:
            self.root.config(cursor="watch")
        else:
            self.root.config(cursor="")
        self.root.update_idletasks()

    def load_notes(self):
        self.listbox.delete(0, tk.END)
        if not os.path.exists(LOCAL_NOTES_DIR):
            try:
                os.makedirs(LOCAL_NOTES_DIR)
            except OSError as e: # More specific error
                messagebox.showerror("Directory Error", f"Failed to create notes directory '{LOCAL_NOTES_DIR}': {e}")
                self.set_status(f"Error: Failed to create notes directory: {e}")
                return

        try:
            for filename in os.listdir(LOCAL_NOTES_DIR):
                if filename.endswith(".txt"):
                    self.listbox.insert(tk.END, filename[:-4])
        except OSError as e: # Catch potential errors listing directory
            messagebox.showerror("File System Error", f"Failed to list notes in '{LOCAL_NOTES_DIR}': {e}")
            self.set_status(f"Error: Failed to list notes: {e}")


    def display_note_content(self, event):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            # This can happen if the list is reloaded and selection is lost
            # self.text_area.delete(1.0, tk.END) # Clear text area if no selection
            return
        
        selected_note_title = self.listbox.get(selected_indices[0])
        filepath = os.path.join(LOCAL_NOTES_DIR, f"{selected_note_title}.txt")
        
        try:
            with open(filepath, "r", encoding='utf-8') as f: # Specify encoding
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, f.read())
            self.set_status(f"Viewing: {selected_note_title}")
        except FileNotFoundError:
            messagebox.showerror("Error", f"Note file '{selected_note_title}.txt' not found. It might have been deleted externally.")
            self.load_notes() # Refresh list
            self.text_area.delete(1.0, tk.END)
        except IOError as e: # More specific error
            messagebox.showerror("File Read Error", f"Could not read note '{selected_note_title}':\n{e}")
            self.set_status(f"Error reading note: {e}")
        except Exception as e: # Catch-all for other unexpected errors
            messagebox.showerror("Error", f"An unexpected error occurred while loading note '{selected_note_title}':\n{e}")
            self.set_status(f"Error loading note: {e}")


    def save_note(self):
        content = self.text_area.get(1.0, tk.END).strip()
        selected_indices = self.listbox.curselection()

        if selected_indices: # Existing note
            note_title = self.listbox.get(selected_indices[0])
        else: # New note
            note_title = simpledialog.askstring("New Note Title", "Enter a title for your new note:")
            if not note_title: # User cancelled or entered empty title
                self.set_status("Save cancelled by user.")
                return
            
            # Basic sanitization for filename
            # A more robust approach might involve a whitelist or more complex regex
            # For now, this covers common problematic characters for many OS.
            invalid_chars = '/\\:*?"<>|' 
            if any(char in note_title for char in invalid_chars):
                messagebox.showerror("Invalid Title", f"Note title cannot contain any of these characters: {invalid_chars}")
                self.set_status("Save failed: Invalid characters in title.")
                return
            
            if os.path.exists(os.path.join(LOCAL_NOTES_DIR, f"{note_title}.txt")):
                # Keeping the original behavior: error if title exists.
                # Alternative: Offer overwrite or rename.
                # if not messagebox.askyesno("Overwrite Confirmation", f"A note with title '{note_title}' already exists. Overwrite it?"):
                #     self.set_status(f"Save cancelled: '{note_title}' already exists.")
                #     return
                messagebox.showerror("Title Exists", f"A note with title '{note_title}' already exists. Please choose a different title.")
                self.set_status(f"Save failed: '{note_title}' already exists.")
                return
        
        filepath = os.path.join(LOCAL_NOTES_DIR, f"{note_title}.txt")
        try:
            with open(filepath, "w", encoding='utf-8') as f: # Specify encoding
                f.write(content)
            
            self.set_status(f"Note '{note_title}' saved successfully.")
            self.load_notes() # Refresh the list
            
            # Reselect the saved note
            try:
                # Get all items from listbox (note titles)
                all_notes_in_listbox = self.listbox.get(0, tk.END)
                if note_title in all_notes_in_listbox:
                    idx = all_notes_in_listbox.index(note_title)
                    self.listbox.selection_set(idx)
                    self.listbox.activate(idx)
                    self.listbox.see(idx) # Ensure it's visible
            except tk.TclError as e: # Catch error if listbox is empty or item not found
                print(f"TclError during reselection (likely listbox empty or item not found): {e}")
            except Exception as e:
                print(f"Unexpected error during reselection: {e}")

        except IOError as e: # More specific error
            messagebox.showerror("File Save Error", f"Could not save note '{note_title}':\n{e}")
            self.set_status(f"Error saving note: {e}")
        except Exception as e: # Catch-all
            messagebox.showerror("Error", f"An unexpected error occurred while saving note '{note_title}':\n{e}")
            self.set_status(f"Error saving note: {e}")


    def new_note(self):
        self.text_area.delete(1.0, tk.END)
        self.listbox.selection_clear(0, tk.END)
        self.text_area.focus_set()
        self.set_status("New note created. Ready for input.")

    def delete_note(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Delete Note", "No note selected to delete.")
            self.set_status("Delete failed: No note selected.")
            return

        selected_note_title = self.listbox.get(selected_indices[0])
        
        # Updated dialog message for clarity
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the local note '{selected_note_title}'?\n\n(This will not delete from Google Drive until the next sync.)"):
            filepath = os.path.join(LOCAL_NOTES_DIR, f"{selected_note_title}.txt")
            try:
                os.remove(filepath)
                self.text_area.delete(1.0, tk.END)
                self.load_notes() # Refresh the list
                self.set_status(f"Note '{selected_note_title}' deleted locally.")
            except FileNotFoundError:
                messagebox.showerror("Delete Error", f"Note file '{selected_note_title}.txt' not found. It might have been already deleted.")
                self.load_notes() # Refresh list
                self.set_status(f"Delete failed: '{selected_note_title}.txt' not found.")
            except OSError as e: # More specific
                messagebox.showerror("File Delete Error", f"Could not delete note '{selected_note_title}':\n{e}")
                self.set_status(f"Error deleting note: {e}")
            except Exception as e: # Catch-all
                messagebox.showerror("Error", f"An unexpected error occurred while deleting note '{selected_note_title}':\n{e}")
                self.set_status(f"Error deleting note: {e}")
        else:
            self.set_status(f"Deletion of '{selected_note_title}' cancelled.")


    def sync_with_drive(self):
        if not self.drive_service:
            messagebox.showerror("Sync Error", "Google Drive is not authenticated. Cannot sync. Try restarting the application or check credentials.")
            self.set_status("Sync failed: Drive not authenticated.")
            if hasattr(self, 'sync_button'): self.sync_button.config(state=tk.DISABLED)
            return

        self.set_status("Syncing with Google Drive...", busy=True)

        try:
            drive_folder_id = get_or_create_app_folder(self.drive_service)
            
            if not drive_folder_id:
                messagebox.showerror("Sync Error", "Could not access Google Drive app folder. Ensure 'drive.appdata' scope was granted and check permissions.")
                self.set_status("Sync failed: Could not get Drive app folder.", busy=False)
                return

            if not os.path.exists(LOCAL_NOTES_DIR):
                try:
                    os.makedirs(LOCAL_NOTES_DIR)
                except OSError as e:
                    messagebox.showerror("Directory Error", f"Failed to create notes directory '{LOCAL_NOTES_DIR}' for sync: {e}")
                    self.set_status(f"Sync failed: Dir creation error: {e}", busy=False)
                    return
            
            # Assuming synchronize_notes will be updated to return True/False or raise specific exceptions
            sync_result = synchronize_notes(self.drive_service, LOCAL_NOTES_DIR, drive_folder_id)
            
            if sync_result: # If synchronize_notes indicates success (e.g. by returning True)
                self.set_status("Sync with Google Drive complete!", busy=False)
                messagebox.showinfo("Sync Complete", "Notes synchronized with Google Drive successfully.")
            else: # If synchronize_notes indicates failure (e.g. by returning False)
                 # Specific error should have been logged by synchronize_notes
                messagebox.showerror("Synchronization Failed", "Synchronization with Google Drive failed. Check logs for details.")
                self.set_status("Sync failed. Check console/logs.", busy=False)

            self.load_notes() # Refresh the local notes list in the UI

        except Exception as e: # Catch errors from get_or_create_app_folder or other unexpected issues
            self.set_status(f"Sync failed: {str(e)[:100]}", busy=False)
            messagebox.showerror("Synchronization Error", f"An unexpected error occurred during synchronization: {e}")
        finally:
            self.set_busy_cursor(False) # Ensure cursor is reset


def main():
    root = tk.Tk()
    app = NoteTakingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
