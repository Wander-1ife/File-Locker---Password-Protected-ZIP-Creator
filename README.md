# File Locker - Password-Protected ZIP Creator

## Overview
File Locker is a Python-based GUI application that allows users to compress and password-protect files or folders into a ZIP archive. The application uses the `pyzipper` library to ensure AES encryption for secure file storage.

## Features
- Select a file or folder for compression
- Apply AES encryption with a user-defined password
- Automatically delete the original file/folder after encryption
- Simple and user-friendly GUI built with `customtkinter`
- Supports both dark and light mode appearances

## Requirements
To run the application, ensure you have the following dependencies installed:

```bash
pip install pyzipper customtkinter
```

## Usage
1. Launch the application by running the script:
   ```bash
   python file_locker.py
   ```
2. Click "Browse File" or "Browse Folder" to select the item to be compressed.
3. Enter a password to protect the ZIP file.
4. Click "Create Password-Protected Zip" to complete the process.
5. The original file/folder will be deleted after encryption.

## Notes
- The application securely encrypts files using AES encryption, ensuring strong protection.
- If you forget the password, there is no way to recover the data.

## Author
- **Creator:** Sami-Ur-Rehman

## Disclaimer
This tool is intended for legal and ethical use only. The developer is not responsible for any misuse of the application.

