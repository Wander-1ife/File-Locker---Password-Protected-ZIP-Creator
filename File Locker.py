import os
import shutil
import threading
import hashlib
import json
import logging
import secrets
import time
from datetime import datetime
from pathlib import Path

import pyzipper
import customtkinter as ctk
from tkinter import filedialog, messagebox

# ─────────────────────────────────────────────
#  Logging setup
# ─────────────────────────────────────────────
LOG_DIR = Path.home() / ".filelocker"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "activity.log"
CONFIG_FILE = LOG_DIR / "config.json"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ─────────────────────────────────────────────
#  Config helpers
# ─────────────────────────────────────────────
DEFAULT_CONFIG = {
    "appearance": "dark",
    "theme": "blue",
    "output_dir": "",
    "delete_original": True,
    "recent": [],
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ─────────────────────────────────────────────
#  Core logic  (no GUI imports here)
# ─────────────────────────────────────────────
def password_strength(pw: str) -> tuple[int, str]:
    """Return (score 0-4, label)."""
    score = 0
    if len(pw) >= 8:  score += 1
    if len(pw) >= 12: score += 1
    if any(c.isdigit() for c in pw):      score += 1
    if any(not c.isalnum() for c in pw):  score += 1
    labels = ["Very Weak", "Weak", "Fair", "Strong", "Very Strong"]
    return score, labels[score]

def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def zip_and_protect(
    source_path: str,
    password: str,
    output_dir: str | None,
    delete_original: bool,
    progress_cb=None,
) -> tuple[bool, str, str]:
    """
    Returns (success, message, zip_path).
    progress_cb(pct: float) is called during compression.
    """
    source = Path(source_path)
    dest_dir = Path(output_dir) if output_dir else source.parent
    zip_path = dest_dir / (source.name + ".zip")

    try:
        # Gather files
        if source.is_dir():
            all_files = [p for p in source.rglob("*") if p.is_file()]
        else:
            all_files = [source]

        total = max(len(all_files), 1)

        with pyzipper.AESZipFile(zip_path, "w", compression=pyzipper.ZIP_DEFLATED) as zf:
            zf.setpassword(password.encode())
            zf.setencryption(pyzipper.WZ_AES)
            for idx, fp in enumerate(all_files, 1):
                if source.is_dir():
                    arcname = fp.relative_to(source)
                else:
                    arcname = fp.name
                zf.write(fp, arcname=str(arcname))
                if progress_cb:
                    progress_cb(idx / total)

        # Compute hash
        file_hash = sha256_of_file(str(zip_path))

        # Delete originals
        if delete_original:
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()

        logging.info(f"LOCKED | {source_path} → {zip_path} | SHA256={file_hash}")
        return True, f"Locked successfully!\n\nSaved to:\n{zip_path}\n\nSHA-256:\n{file_hash}", str(zip_path)

    except Exception as e:
        logging.error(f"LOCK FAILED | {source_path} | {e}")
        return False, str(e), ""


def unzip_protected(
    zip_path: str,
    password: str,
    output_dir: str | None,
    progress_cb=None,
) -> tuple[bool, str]:
    """Returns (success, message)."""
    src = Path(zip_path)
    dest = Path(output_dir) if output_dir else src.parent / src.stem

    try:
        with pyzipper.AESZipFile(src, "r") as zf:
            zf.setpassword(password.encode())
            members = zf.namelist()
            total = max(len(members), 1)
            for idx, member in enumerate(members, 1):
                zf.extract(member, path=str(dest))
                if progress_cb:
                    progress_cb(idx / total)

        logging.info(f"UNLOCKED | {zip_path} → {dest}")
        return True, f"Extracted to:\n{dest}"
    except RuntimeError:
        logging.warning(f"UNLOCK FAILED (bad password) | {zip_path}")
        return False, "Wrong password or corrupted archive."
    except Exception as e:
        logging.error(f"UNLOCK FAILED | {zip_path} | {e}")
        return False, str(e)


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────
STRENGTH_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c"]

class FileLockApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        ctk.set_appearance_mode(self.cfg["appearance"])
        ctk.set_default_color_theme(self.cfg["theme"])

        self.title("File Locker")
        self.geometry("560x620")
        self.resizable(False, False)

        self._build_ui()

    # ── UI construction ──────────────────────
    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(top, text="🔒 File Locker", font=("Helvetica", 20, "bold")).pack(side="left")

        # Theme toggle
        self._appearance_var = ctk.StringVar(value=self.cfg["appearance"].capitalize())
        ctk.CTkOptionMenu(
            top, values=["Dark", "Light", "System"],
            variable=self._appearance_var,
            width=100,
            command=self._change_appearance,
        ).pack(side="right")

        # Tabs
        self.tabs = ctk.CTkTabview(self, width=520)
        self.tabs.pack(padx=20, pady=12, fill="both", expand=True)
        self.tabs.add("🔐  Lock")
        self.tabs.add("🔓  Unlock")
        self.tabs.add("⚙️  Settings")

        self._build_lock_tab()
        self._build_unlock_tab()
        self._build_settings_tab()

        # Footer
        ctk.CTkLabel(
            self, text="Creator: Sami-Ur-Rehman",
            font=("Helvetica", 10), text_color="gray"
        ).pack(side="bottom", pady=8)

        self.bind("<Return>", lambda _: self._on_enter())

    def _section(self, parent, label):
        ctk.CTkLabel(parent, text=label, font=("Helvetica", 12, "bold")).pack(
            anchor="w", pady=(10, 2)
        )

    # ── Lock tab ─────────────────────────────
    def _build_lock_tab(self):
        tab = self.tabs.tab("🔐  Lock")

        self._section(tab, "Source")
        src_row = ctk.CTkFrame(tab, fg_color="transparent")
        src_row.pack(fill="x")
        self.lock_path = ctk.CTkEntry(src_row, placeholder_text="Select file or folder…", width=320)
        self.lock_path.pack(side="left", padx=(0, 6))
        ctk.CTkButton(src_row, text="File", width=72, command=self._browse_file).pack(side="left", padx=2)
        ctk.CTkButton(src_row, text="Folder", width=72, command=self._browse_folder).pack(side="left", padx=2)

        # Recent
        self._section(tab, "Recent")
        self._recent_var = ctk.StringVar(value="Pick a recent path…")
        self._recent_menu = ctk.CTkOptionMenu(
            tab, variable=self._recent_var,
            values=self._recent_values(),
            width=460,
            command=self._pick_recent,
        )
        self._recent_menu.pack(anchor="w")

        # Password
        self._section(tab, "Password")
        pw_row = ctk.CTkFrame(tab, fg_color="transparent")
        pw_row.pack(fill="x")
        self.lock_pw = ctk.CTkEntry(pw_row, show="*", placeholder_text="Enter password…", width=390)
        self.lock_pw.pack(side="left")
        self.lock_pw.bind("<KeyRelease>", lambda _: self._update_strength())
        self._show_lock = False
        ctk.CTkButton(pw_row, text="👁", width=40, command=self._toggle_lock_pw).pack(side="left", padx=6)

        # Confirm password
        conf_row = ctk.CTkFrame(tab, fg_color="transparent")
        conf_row.pack(fill="x", pady=(4, 0))
        self.lock_pw_confirm = ctk.CTkEntry(conf_row, show="*", placeholder_text="Confirm password…", width=390)
        self.lock_pw_confirm.pack(side="left")

        # Strength bar
        self.strength_bar = ctk.CTkProgressBar(tab, width=460, height=8)
        self.strength_bar.set(0)
        self.strength_bar.pack(pady=(6, 0), anchor="w")
        self.strength_label = ctk.CTkLabel(tab, text="", font=("Helvetica", 10))
        self.strength_label.pack(anchor="w")

        # Delete original checkbox
        self._delete_var = ctk.BooleanVar(value=self.cfg["delete_original"])
        ctk.CTkCheckBox(tab, text="Delete original after locking", variable=self._delete_var).pack(
            anchor="w", pady=(8, 0)
        )

        # Progress
        self.lock_progress = ctk.CTkProgressBar(tab, width=460)
        self.lock_progress.set(0)
        self.lock_progress.pack(pady=(10, 0), anchor="w")

        self.lock_status = ctk.CTkLabel(tab, text="", font=("Helvetica", 10), text_color="gray")
        self.lock_status.pack(anchor="w")

        ctk.CTkButton(
            tab, text="🔐  Lock & Encrypt", height=40,
            font=("Helvetica", 13, "bold"), command=self._do_lock
        ).pack(pady=(12, 0), fill="x")

    # ── Unlock tab ───────────────────────────
    def _build_unlock_tab(self):
        tab = self.tabs.tab("🔓  Unlock")

        self._section(tab, "ZIP File")
        zip_row = ctk.CTkFrame(tab, fg_color="transparent")
        zip_row.pack(fill="x")
        self.unlock_path = ctk.CTkEntry(zip_row, placeholder_text="Select ZIP file…", width=380)
        self.unlock_path.pack(side="left", padx=(0, 6))
        ctk.CTkButton(zip_row, text="Browse", width=80, command=self._browse_zip).pack(side="left")

        self._section(tab, "Output Folder (optional)")
        out_row = ctk.CTkFrame(tab, fg_color="transparent")
        out_row.pack(fill="x")
        self.unlock_out = ctk.CTkEntry(out_row, placeholder_text="Default: next to ZIP file", width=380)
        self.unlock_out.pack(side="left", padx=(0, 6))
        ctk.CTkButton(out_row, text="Browse", width=80, command=self._browse_unlock_out).pack(side="left")

        self._section(tab, "Password")
        pw_row = ctk.CTkFrame(tab, fg_color="transparent")
        pw_row.pack(fill="x")
        self.unlock_pw = ctk.CTkEntry(pw_row, show="*", placeholder_text="Enter password…", width=390)
        self.unlock_pw.pack(side="left")
        self._show_unlock = False
        ctk.CTkButton(pw_row, text="👁", width=40, command=self._toggle_unlock_pw).pack(side="left", padx=6)

        self.unlock_progress = ctk.CTkProgressBar(tab, width=460)
        self.unlock_progress.set(0)
        self.unlock_progress.pack(pady=(14, 0), anchor="w")

        self.unlock_status = ctk.CTkLabel(tab, text="", font=("Helvetica", 10), text_color="gray")
        self.unlock_status.pack(anchor="w")

        ctk.CTkButton(
            tab, text="🔓  Decrypt & Extract", height=40,
            font=("Helvetica", 13, "bold"), command=self._do_unlock
        ).pack(pady=(12, 0), fill="x")

    # ── Settings tab ─────────────────────────
    def _build_settings_tab(self):
        tab = self.tabs.tab("⚙️  Settings")

        self._section(tab, "Default Output Directory")
        out_row = ctk.CTkFrame(tab, fg_color="transparent")
        out_row.pack(fill="x")
        self.settings_out = ctk.CTkEntry(out_row, placeholder_text="Same as source (default)", width=380)
        if self.cfg["output_dir"]:
            self.settings_out.insert(0, self.cfg["output_dir"])
        self.settings_out.pack(side="left", padx=(0, 6))
        ctk.CTkButton(out_row, text="Browse", width=80, command=self._browse_settings_out).pack(side="left")

        self._section(tab, "Log File")
        ctk.CTkLabel(tab, text=str(LOG_FILE), font=("Helvetica", 10), text_color="gray").pack(anchor="w")
        ctk.CTkButton(tab, text="Open Log Folder", width=160, command=self._open_log_folder).pack(
            anchor="w", pady=(6, 0)
        )

        self._section(tab, "Clear Recent History")
        ctk.CTkButton(tab, text="Clear Recents", width=140, command=self._clear_recents).pack(anchor="w", pady=4)

        ctk.CTkButton(
            tab, text="💾  Save Settings", height=38,
            font=("Helvetica", 12, "bold"), command=self._save_settings
        ).pack(pady=(20, 0), fill="x")

    # ── Helpers ──────────────────────────────
    def _change_appearance(self, val):
        ctk.set_appearance_mode(val)
        self.cfg["appearance"] = val.lower()
        save_config(self.cfg)

    def _toggle_lock_pw(self):
        self._show_lock = not self._show_lock
        self.lock_pw.configure(show="" if self._show_lock else "*")

    def _toggle_unlock_pw(self):
        self._show_unlock = not self._show_unlock
        self.unlock_pw.configure(show="" if self._show_unlock else "*")

    def _update_strength(self):
        pw = self.lock_pw.get()
        score, label = password_strength(pw)
        self.strength_bar.set(score / 4)
        self.strength_bar.configure(progress_color=STRENGTH_COLORS[score])
        self.strength_label.configure(text=f"Strength: {label}", text_color=STRENGTH_COLORS[score])

    def _browse_file(self):
        p = filedialog.askopenfilename()
        if p:
            self.lock_path.delete(0, ctk.END)
            self.lock_path.insert(0, p)

    def _browse_folder(self):
        p = filedialog.askdirectory()
        if p:
            self.lock_path.delete(0, ctk.END)
            self.lock_path.insert(0, p)

    def _browse_zip(self):
        p = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if p:
            self.unlock_path.delete(0, ctk.END)
            self.unlock_path.insert(0, p)

    def _browse_unlock_out(self):
        p = filedialog.askdirectory()
        if p:
            self.unlock_out.delete(0, ctk.END)
            self.unlock_out.insert(0, p)

    def _browse_settings_out(self):
        p = filedialog.askdirectory()
        if p:
            self.settings_out.delete(0, ctk.END)
            self.settings_out.insert(0, p)

    def _recent_values(self):
        r = self.cfg.get("recent", [])
        return r if r else ["(no recent paths)"]

    def _pick_recent(self, val):
        if val and val != "(no recent paths)":
            self.lock_path.delete(0, ctk.END)
            self.lock_path.insert(0, val)

    def _add_to_recent(self, path: str):
        recent = self.cfg.get("recent", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.cfg["recent"] = recent[:10]
        save_config(self.cfg)
        self._recent_menu.configure(values=self._recent_values())

    def _clear_recents(self):
        self.cfg["recent"] = []
        save_config(self.cfg)
        self._recent_menu.configure(values=["(no recent paths)"])
        messagebox.showinfo("Done", "Recent history cleared.")

    def _open_log_folder(self):
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(LOG_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", LOG_DIR])
        else:
            subprocess.Popen(["xdg-open", LOG_DIR])

    def _save_settings(self):
        self.cfg["output_dir"] = self.settings_out.get().strip()
        save_config(self.cfg)
        messagebox.showinfo("Saved", "Settings saved.")

    def _on_enter(self):
        tab = self.tabs.get()
        if "Lock" in tab:
            self._do_lock()
        elif "Unlock" in tab:
            self._do_unlock()

    # ── Lock action ──────────────────────────
    def _do_lock(self):
        source = self.lock_path.get().strip()
        pw = self.lock_pw.get()
        pw_confirm = self.lock_pw_confirm.get()
        out = self.cfg.get("output_dir") or None

        if not source:
            messagebox.showwarning("Required", "Please select a file or folder.")
            return
        if not pw:
            messagebox.showwarning("Required", "Please enter a password.")
            return
        if pw != pw_confirm:
            messagebox.showerror("Mismatch", "Passwords do not match.")
            return
        score, label = password_strength(pw)
        if score < 2:
            if not messagebox.askyesno("Weak Password",
                f"Password strength is '{label}'. Proceed anyway?"):
                return
        if self._delete_var.get():
            if not messagebox.askyesno("Confirm Deletion",
                "The original file/folder will be permanently deleted after locking.\n\nContinue?"):
                return

        self.lock_status.configure(text="Encrypting…", text_color="gray")
        self.lock_progress.set(0)

        def run():
            ok, msg, zip_path = zip_and_protect(
                source, pw, out, self._delete_var.get(),
                progress_cb=lambda p: self.after(0, self.lock_progress.set, p),
            )
            # Wipe password from memory
            pw_bytes = pw.encode()
            secrets.token_bytes(len(pw_bytes))

            def finish():
                self.lock_progress.set(1 if ok else 0)
                self.lock_status.configure(
                    text="Done ✓" if ok else "Failed ✗",
                    text_color="#2ecc71" if ok else "#e74c3c",
                )
                if ok:
                    self._add_to_recent(source)
                    messagebox.showinfo("Success", msg)
                else:
                    messagebox.showerror("Error", msg)
            self.after(0, finish)

        threading.Thread(target=run, daemon=True).start()

    # ── Unlock action ────────────────────────
    def _do_unlock(self):
        zip_path = self.unlock_path.get().strip()
        pw = self.unlock_pw.get()
        out = self.unlock_out.get().strip() or None

        if not zip_path:
            messagebox.showwarning("Required", "Please select a ZIP file.")
            return
        if not pw:
            messagebox.showwarning("Required", "Please enter the password.")
            return

        self.unlock_status.configure(text="Decrypting…", text_color="gray")
        self.unlock_progress.set(0)

        def run():
            ok, msg = unzip_protected(
                zip_path, pw, out,
                progress_cb=lambda p: self.after(0, self.unlock_progress.set, p),
            )

            def finish():
                self.unlock_progress.set(1 if ok else 0)
                self.unlock_status.configure(
                    text="Done ✓" if ok else "Failed ✗",
                    text_color="#2ecc71" if ok else "#e74c3c",
                )
                if ok:
                    messagebox.showinfo("Success", msg)
                else:
                    messagebox.showerror("Error", msg)
            self.after(0, finish)

        threading.Thread(target=run, daemon=True).start()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = FileLockApp()
    app.mainloop()