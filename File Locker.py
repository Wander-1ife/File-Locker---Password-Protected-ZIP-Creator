import os
import shutil
import pyzipper
import customtkinter as ctk
from tkinter import filedialog, messagebox

def zip_and_protect(source_path, password):
    # Get the directory and zip file name
    source_dir = os.path.dirname(source_path)
    zip_name = os.path.basename(source_path) + ".zip"
    zip_path = os.path.join(source_dir, zip_name)
    
    try:
        # Create the zip file with password protection
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED) as zip_file:
            zip_file.setpassword(password.encode())
            zip_file.setencryption(pyzipper.WZ_AES)  # Ensure AES encryption is set
            
            # Check if it's a file or directory
            if os.path.isdir(source_path):
                # Add all files in the folder to the zip file
                for root, _, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_path)
                        zip_file.write(file_path, arcname=arcname)
            else:
                # Add the single file to the zip file
                zip_file.write(source_path, arcname=os.path.basename(source_path))
        
        # Delete the original file or folder
        if os.path.isdir(source_path):
            shutil.rmtree(source_path)
        else:
            os.remove(source_path)
        
        messagebox.showinfo("Success", f"'{source_path}' has been zipped to '{zip_path}' with password protection.")
    
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def browse_file():
    # Open file dialog to select a file
    file_path = filedialog.askopenfilename()
    if file_path:
        entry_path.delete(0, ctk.END)
        entry_path.insert(0, file_path)

def browse_folder():
    # Open file dialog to select a folder
    folder_path = filedialog.askdirectory()
    if folder_path:
        entry_path.delete(0, ctk.END)
        entry_path.insert(0, folder_path)

def create_zip():
    source_path = entry_path.get().strip()
    password = entry_password.get().strip()
    
    if not source_path:
        messagebox.showwarning("Input Required", "Please select a file or folder.")
        return
    if not password:
        messagebox.showwarning("Input Required", "Please enter a password.")
        return
    
    zip_and_protect(source_path, password)

# Initialize customtkinter and configure theme
ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

# Create the main application window
app = ctk.CTk()
app.title("File Locker")
app.geometry("500x350")  # Increased size for better visibility
app.resizable(False, False)  # Fixed window size for user

# Create and arrange widgets
ctk.CTkLabel(app, text="File/Folder Path:", font=("Helvetica", 12)).pack(pady=10)
entry_path = ctk.CTkEntry(app, width=400)
entry_path.pack(pady=5)

# Two separate buttons for browsing file and folder
browse_file_button = ctk.CTkButton(app, text="Browse File", command=browse_file)
browse_file_button.pack(pady=5)

browse_folder_button = ctk.CTkButton(app, text="Browse Folder", command=browse_folder)
browse_folder_button.pack(pady=5)

ctk.CTkLabel(app, text="Password:", font=("Helvetica", 12)).pack(pady=10)
entry_password = ctk.CTkEntry(app, show="*", width=400)
entry_password.pack(pady=5)

create_zip_button = ctk.CTkButton(app, text="Create Password-Protected Zip", command=create_zip)
create_zip_button.pack(pady=20)

# Add the "Creator" label at the end
ctk.CTkLabel(app, text="Creator: Sami-Ur-Rehman", font=("Helvetica", 10)).pack(side=ctk.BOTTOM, pady=10)

# Bind the Enter key to the create_zip function
app.bind('<Return>', lambda event: create_zip())

# Run the application
app.mainloop()
