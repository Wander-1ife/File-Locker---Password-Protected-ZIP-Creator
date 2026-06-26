# 🔒 File Locker — Password-Protected ZIP Creator

A Python GUI application that compresses and AES-encrypts files or folders into password-protected ZIP archives. Built with `customtkinter` for a clean, modern interface with dark and light mode support.

---

## Features

- AES-256 encryption via `pyzipper`
- Lock files or entire folders into a password-protected ZIP
- Unlock / decrypt and extract existing protected ZIPs
- Password strength meter (Very Weak → Very Strong) with live color feedback
- Password confirmation field to prevent lockout from typos
- Show / hide password toggle on all password fields
- Weak password warning before proceeding
- Confirmation dialog before deleting the original file or folder
- Real-time progress bar — stays responsive during large file operations (background threading)
- SHA-256 hash displayed after locking so you can verify the ZIP later
- Recent paths dropdown — last 10 locked paths remembered across sessions
- Configurable default output directory — save ZIPs anywhere, not just next to the source
- Activity log at `~/.filelocker/activity.log` with timestamps and SHA-256 hashes
- Appearance switcher (Dark / Light / System) in the top bar, persisted to config
- Settings tab for output directory, log access, and clearing history

---

## Requirements

**Python 3.10+** and:

```
pip install pyzipper customtkinter
```

> **Important:** install into the same Python you run the script with:
> ```
> C:\path\to\your\python.exe -m pip install pyzipper customtkinter
> ```

---

## Usage

### Launch

```
python file_locker.py
```

### Lock tab — encrypt a file or folder

1. Click **File** or **Folder** to browse, or pick a path from the **Recent** dropdown
2. Enter a password — the strength meter updates live
3. Confirm the password in the second field
4. Optionally uncheck **Delete original after locking** to keep the source
5. Click **🔐 Lock & Encrypt**
6. A success dialog shows the ZIP path and its SHA-256 hash

### Unlock tab — decrypt and extract

1. Click **Browse** to select a `.zip` file
2. Optionally set a custom output folder (defaults to next to the ZIP)
3. Enter the password
4. Click **🔓 Decrypt & Extract**

### Settings tab

- Set a **default output directory** for all ZIPs
- **Open log folder** to view `activity.log`
- **Clear recent history** to reset the dropdown

---

## Example Log Entry

```
2025-06-27 14:01:33 | INFO | LOCKED | D:\docs\contracts → D:\docs\contracts.zip | SHA256=9d4e7b...
2025-06-27 14:05:10 | INFO | UNLOCKED | D:\docs\contracts.zip → D:\docs\contracts
```

---

## Settings Reference

All preferences are saved automatically to `~/.filelocker/config.json`:

| Setting | Description |
|---|---|
| Output directory | Where ZIPs are saved (default: same folder as source) |
| Appearance | Dark / Light / System |
| Delete original | Whether to remove source after locking |
| Recent paths | Last 10 locked paths (max) |

---

## Notes

- AES-256 encryption is used — the ZIP cannot be opened without the correct password
- **If you forget the password, the data cannot be recovered** — there is no backdoor
- The original file or folder is only deleted after the ZIP is successfully created
- All operations run in a background thread — the UI never freezes during large transfers
- Quoted paths from drag-and-drop are handled automatically

---

## Disclaimer

This tool is intended for legal and ethical use only. The developer is not responsible for any misuse of the application.
