"""
Email → Google Sheets — macOS desktop app.
Wraps the itselectric pipeline in a CustomTkinter GUI.
"""

import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
import yaml

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DARK_BG      = "#0f1117"
CARD_BG      = "#1a1d27"
ACCENT       = "#4f8ef7"
ACCENT_HOVER = "#3a7ae8"
SUCCESS      = "#22c55e"
ERROR        = "#ef4444"
TEXT_PRIMARY = "#f0f2f8"
TEXT_MUTED   = "#6b7280"
BORDER       = "#2a2d3e"


# ── Stdout capture ─────────────────────────────────────────────────────────────
class _LogWriter:
    """Redirects print() output to a GUI callback (thread-safe via after())."""

    def __init__(self, callback):
        self._callback = callback
        self._orig = sys.__stdout__

    def write(self, text):
        if text and text.strip():
            self._callback(text.rstrip())
            self._orig.write(text)
            self._orig.flush()

    def flush(self):
        self._orig.flush()


# ── Main App ───────────────────────────────────────────────────────────────────
class EmailSheetsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fix HiDPI/Retina scaling on macOS.
        #
        # Tk geometry() always uses physical screen pixels. The base window size
        # is defined in logical units, so we multiply by the actual scale factor
        # to get the correct physical size.
        #
        # PyInstaller's bundled Tcl/Tk sometimes reports scale=1.0 on Retina.
        # We detect this by checking whether the physical screen resolution looks
        # Retina (≥2560 wide or ≥1600 tall) and force 2.0 if so.
        self._tk_scale = 1.0
        if sys.platform == "darwin":
            try:
                current = float(self.tk.call("tk", "scaling"))
                if current >= 1.5:
                    # Correctly detected — use it as-is
                    self._tk_scale = current
                else:
                    # Low scale reported — check physical resolution to decide
                    if self.winfo_screenwidth() >= 2560 or self.winfo_screenheight() >= 1600:
                        self.tk.call("tk", "scaling", 2.0)
                        self._tk_scale = 2.0
                    # else: genuine non-Retina display, leave at 1.0
            except Exception:
                pass

        # Base logical size — scaled up to physical pixels when on Retina
        base_w, base_h = 560, 660
        phys_w = int(base_w * self._tk_scale)
        phys_h = int(base_h * self._tk_scale)

        self.title("it's electric automation")
        self.geometry(f"{phys_w}x{phys_h}")
        self.resizable(False, False)
        self.configure(fg_color=DARK_BG)

        self._yaml_path = ctk.StringVar(value="")
        self._running   = False

        self._build_ui(self._tk_scale)

    # ── UI Construction ────────────────────────────────────────────────────────
    def _build_ui(self, scale: float = 1.0):
        # scale is used for fixed-pixel dimensions (header, log, status badge)
        # so they fill the window correctly on both Retina and non-Retina.
        def px(n):
            return int(n * scale)

        # Header
        header = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=px(64))
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="it's electric automation",
            font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Body card
        card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        card.pack(fill="both", expand=True, padx=24, pady=20)

        # Config file picker
        ctk.CTkLabel(
            card,
            text="CONFIG FILE  (.yaml / .yml)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=24, pady=(24, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24)

        self._path_entry = ctk.CTkEntry(
            row,
            textvariable=self._yaml_path,
            placeholder_text="Select your config.yaml …",
            fg_color="#12151f",
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            height=40,
            corner_radius=8,
        )
        self._path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            row,
            text="Browse",
            width=80,
            height=40,
            fg_color="#23263a",
            hover_color="#2e3250",
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            command=self._browse,
        ).pack(side="right")

        # Divider
        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=16)

        # Log output
        ctk.CTkLabel(
            card,
            text="OUTPUT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=24, pady=(0, 6))

        self._log = ctk.CTkTextbox(
            card,
            height=px(220),
            fg_color="#12151f",
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Courier New", size=12),
            corner_radius=8,
            state="disabled",
            wrap="word",
        )
        self._log.pack(fill="x", padx=24)

        # Divider
        ctk.CTkFrame(card, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=16)

        # Status badge
        self._status_frame = ctk.CTkFrame(
            card, fg_color="#12151f", corner_radius=10, height=px(52)
        )
        self._status_frame.pack(fill="x", padx=24)
        self._status_frame.pack_propagate(False)

        self._status_dot = ctk.CTkLabel(
            self._status_frame,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
        )
        self._status_dot.place(relx=0.08, rely=0.5, anchor="center")

        self._status_label = ctk.CTkLabel(
            self._status_frame,
            text="Ready — select a config file to begin",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        self._status_label.place(relx=0.55, rely=0.5, anchor="center")

        # Run button
        self._run_btn = ctk.CTkButton(
            card,
            text="▶  Run",
            height=48,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Georgia", size=16, weight="bold"),
            corner_radius=10,
            command=self._on_run,
        )
        self._run_btn.pack(fill="x", padx=24, pady=(16, 24))

    # ── Actions ────────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select config file",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if path:
            self._yaml_path.set(path)
            self._clear_log()
            self._set_status("idle", f"Config loaded: {os.path.basename(path)}")

    def _on_run(self):
        path = self._yaml_path.get().strip()
        if not path:
            self._set_status("error", "Please select a config file first")
            return
        if not os.path.isfile(path):
            self._set_status("error", "File not found — check the path")
            return
        if self._running:
            return

        self._running = True
        self._clear_log()
        self._run_btn.configure(state="disabled", text="Running …")
        self._set_status("running", "Processing emails …")

        threading.Thread(target=self._run_pipeline, args=(path,), daemon=True).start()

    def _run_pipeline(self, yaml_path: str):
        """Run the itselectric pipeline, capturing stdout into the log widget."""
        # Import here so PyInstaller can tree-shake correctly
        from googleapiclient.errors import HttpError

        from itselectric.auth import get_credentials
        from itselectric.extract import extract_parsed
        from itselectric.gmail import (
            body_to_plain,
            fetch_messages,
            format_sent_date,
            get_body_from_payload,
        )
        from itselectric.sheets import append_rows, get_existing_hashes, row_hash

        # Redirect print() to the log widget
        old_stdout = sys.stdout
        sys.stdout = _LogWriter(lambda t: self.after(0, self._append_log, t))
        print(f"Starting pipeline with config: {yaml_path}")

        success, message = True, "Done"
        try:
            # Load config
            with open(yaml_path) as f:
                config = yaml.safe_load(f) or {}

            label         = config.get("label", "INBOX")
            max_messages  = int(config.get("max_messages", 100))
            body_length   = int(config.get("body_length", 200))
            spreadsheet_id = config.get("spreadsheet_id", "").strip()
            sheet_name    = config.get("sheet", "Sheet1")
            content_limit = int(config.get("content_limit", 5000))

            # Resolve credentials relative to config file location
            print("Resolving credentials …")
            config_dir = str(Path(yaml_path).parent)
            token_file       = os.path.join(config_dir, "token.json")
            credentials_file = os.path.join(config_dir, "credentials.json")

            creds = get_credentials(token_file=token_file, credentials_file=credentials_file)
            print("Credentials ready. Getting messages …")
            messages = fetch_messages(creds, label, max_messages)

            print(f"Processing {len(messages)} message(s) …")
            sheet_rows = []
            for msg in messages:
                sent_date = format_sent_date(msg)
                mime_type, body_text = get_body_from_payload(msg.get("payload", {}))
                plain = None
                if body_text is not None:
                    plain = body_to_plain(mime_type, body_text)
                    over = body_length and len(plain) > body_length
                    preview = plain[:body_length] + "..." if over else plain
                    print(f"[plain]: {preview}")
                else:
                    print("No body found for message.")

                if spreadsheet_id:
                    content = plain or ""
                    parsed = extract_parsed(content)
                    if parsed:
                        sheet_rows.append((
                            sent_date,
                            parsed["name"],
                            parsed["address"],
                            parsed["email_1"],
                            parsed["email_2"],
                            content,
                        ))
                    else:
                        sheet_rows.append((sent_date, "", "", "", "", content))

            if spreadsheet_id and sheet_rows:
                existing = get_existing_hashes(creds, spreadsheet_id, sheet_name, content_limit)

                def _hash(r):
                    d, n, a, e1, e2, c = r
                    return row_hash([d, n, a, e1, e2, c], content_limit)

                new_rows = [r for r in sheet_rows if _hash(r) not in existing]
                skipped = len(sheet_rows) - len(new_rows)
                if skipped:
                    print(f"Skipping {skipped} row(s) already on sheet.")
                if new_rows:
                    append_rows(creds, spreadsheet_id, sheet_name, new_rows, content_limit)
                    message = f"Done — {len(new_rows)} row(s) added to sheet."
                    print(message)
                else:
                    message = "All messages already on sheet — nothing added."
                    print(message)
            elif not spreadsheet_id:
                message = f"Preview complete — {len(messages)} message(s) shown."
                print(message)
            else:
                message = "No messages found."

        except HttpError as e:
            success, message = False, f"API error: {e}"
            print(message)
        except FileNotFoundError as e:
            success, message = False, f"File not found: {e}"
            print(message)
        except Exception as e:
            success, message = False, str(e)
            print(f"Error: {e}")
        finally:
            sys.stdout = old_stdout

        self.after(0, self._on_done, success, message)

    def _on_done(self, success: bool, message: str):
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Run")
        self._set_status("success" if success else "error", message)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _append_log(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _set_status(self, state: str, message: str):
        colors = {
            "idle":    TEXT_MUTED,
            "running": "#facc15",
            "success": SUCCESS,
            "error":   ERROR,
        }
        color = colors.get(state, TEXT_MUTED)
        self._status_dot.configure(text_color=color)
        self._status_label.configure(text=message, text_color=color)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = EmailSheetsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
