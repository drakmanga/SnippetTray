#!/usr/bin/env python3
# External dependencies: pystray, Pillow  (pip install pystray Pillow)

import json
import os

# On Wayland (KDE/GNOME), pystray's default X11 backend doesn't receive click
# events. Force the appindicator backend which uses the StatusNotifierItem
# protocol supported by KDE Plasma, GNOME (with extension), etc.
if os.environ.get("WAYLAND_DISPLAY") and "PYSTRAY_BACKEND" not in os.environ:
    os.environ["PYSTRAY_BACKEND"] = "appindicator"
import shlex
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

import pystray
from PIL import Image, ImageDraw


CONFIG_DIR = Path.home() / ".config" / "snippettray"
SNIPPETS_FILE = CONFIG_DIR / "snippets.json"

DEFAULT_SNIPPETS = [
    {
        "command": "apt update && apt upgrade -y",
        "description": "Update system packages (Debian/Ubuntu)",
    },
    {
        "command": "journalctl -xe --no-pager | tail -100",
        "description": "View recent system log entries",
    },
    {
        "command": "df -h && echo && free -h",
        "description": "Check disk and memory usage",
    },
]

ROW_COLORS = ("#ffffff", "#f0f4f8")
HEADER_BG = "#dbe9f7"


# ── Persistence ────────────────────────────────────────────────────────────────

def load_snippets():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SNIPPETS_FILE.exists():
        save_snippets(DEFAULT_SNIPPETS)
        return list(DEFAULT_SNIPPETS)
    try:
        with open(SNIPPETS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return list(DEFAULT_SNIPPETS)


def save_snippets(snippets):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SNIPPETS_FILE, "w") as f:
        json.dump(snippets, f, indent=2)


# ── Terminal execution ──────────────────────────────────────────────────────────

def _build_terminal_cmd(shell_script):
    if shutil.which("konsole"):
        return ["konsole", "-e", "bash", "-c", shell_script]
    if shutil.which("gnome-terminal"):
        return ["gnome-terminal", "--", "bash", "-c", shell_script]
    if shutil.which("xfce4-terminal"):
        return ["xfce4-terminal", "-e", "bash -c " + shlex.quote(shell_script)]
    if shutil.which("xterm"):
        return ["xterm", "-e", "bash", "-c", shell_script]
    return None


def run_snippet(command):
    shell_script = f"sudo {command}"
    args = _build_terminal_cmd(shell_script)
    if args is None:
        messagebox.showerror(
            "No Terminal Found",
            "No terminal emulator was found.\n"
            "Please install one of: konsole, gnome-terminal, xfce4-terminal, xterm",
        )
        return
    subprocess.Popen(args)


# ── Tray icon image ─────────────────────────────────────────────────────────────

def _make_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=(52, 120, 200, 255))
    d.rectangle([12, 18, 52, 24], fill=(255, 255, 255))
    d.rectangle([12, 30, 46, 36], fill=(255, 255, 255))
    d.rectangle([12, 42, 50, 48], fill=(255, 255, 255))
    return img


# ── Snippet dialog ──────────────────────────────────────────────────────────────

class SnippetDialog(tk.Toplevel):
    def __init__(self, parent, *, title="Snippet", command="", description=""):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        pad = {"padx": 12, "pady": 7}

        tk.Label(self, text="Description:", anchor="w").grid(row=0, column=0, sticky="w", **pad)
        self._desc = tk.StringVar(value=description)
        tk.Entry(self, textvariable=self._desc, width=56).grid(row=0, column=1, **pad)

        tk.Label(self, text="Command:", anchor="w").grid(row=1, column=0, sticky="w", **pad)
        self._cmd = tk.StringVar(value=command)
        tk.Entry(self, textvariable=self._cmd, width=56,
                 font=("monospace", 10)).grid(row=1, column=1, **pad)

        btns = tk.Frame(self)
        btns.grid(row=2, column=0, columnspan=2, pady=(4, 12))
        tk.Button(btns, text="Save", width=10, command=self._save).pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", width=10, command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda _: self._save())
        self.bind("<Escape>", lambda _: self.destroy())
        self.transient(parent)

        self.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        sw, sh = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - sw) // 2}+{py + (ph - sh) // 2}")

        self.wait_window()

    def _save(self):
        cmd = self._cmd.get().strip()
        if not cmd:
            messagebox.showwarning("Validation", "Command cannot be empty.", parent=self)
            return
        self.result = {"command": cmd, "description": self._desc.get().strip()}
        self.destroy()


# ── Main window ─────────────────────────────────────────────────────────────────

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.snippets = load_snippets()
        self._build_ui()

    def _build_ui(self):
        self.root.title("SnippetTray")
        self.root.minsize(600, 400)
        self.root.geometry("860x520")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        bar = tk.Frame(self.root, bg="#f0f0f0")
        bar.pack(fill="x")
        tk.Label(bar, text=" SnippetTray", font=("", 13, "bold"),
                 bg="#f0f0f0").pack(side="left", pady=8, padx=6)
        tk.Button(bar, text="+ Add Snippet", command=self._add,
                  bg="#4CAF50", fg="white", activebackground="#388E3C",
                  relief="flat", padx=10).pack(side="right", pady=6, padx=10)

        tk.Frame(self.root, height=1, bg="#c0c0c0").pack(fill="x")

        hdr = tk.Frame(self.root, bg=HEADER_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Description", bg=HEADER_BG,
                 font=("", 9, "bold"), width=30, anchor="w").pack(side="left", pady=5)
        tk.Label(hdr, text="Command", bg=HEADER_BG,
                 font=("", 9, "bold"), anchor="w").pack(side="left", pady=5, fill="x", expand=True)
        tk.Label(hdr, text="Actions", bg=HEADER_BG,
                 font=("", 9, "bold"), anchor="center", width=26).pack(side="right", pady=5, padx=4)

        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(frame, highlightthickness=0, bg="#ffffff")
        sb = tk.Scrollbar(frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._list = tk.Frame(self._canvas, bg="#ffffff")
        self._win = self._canvas.create_window((0, 0), window=self._list, anchor="nw")

        self._list.bind("<Configure>", lambda _: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(
            self._win, width=e.width))
        self._canvas.bind("<Enter>", self._enable_scroll)
        self._canvas.bind("<Leave>", self._disable_scroll)

        self._render()

    def _enable_scroll(self, _=None):
        self._canvas.bind_all("<Button-4>", lambda _: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>", lambda _: self._canvas.yview_scroll(1, "units"))

    def _disable_scroll(self, _=None):
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _render(self):
        for w in self._list.winfo_children():
            w.destroy()

        if not self.snippets:
            tk.Label(self._list,
                     text="No snippets yet.\nClick '+ Add Snippet' to create one.",
                     fg="#888888", bg="#ffffff", pady=40, font=("", 11)).pack()
            return

        for idx, snippet in enumerate(self.snippets):
            self._render_row(idx, snippet)

    def _render_row(self, idx, snippet):
        bg = ROW_COLORS[idx % 2]
        row = tk.Frame(self._list, bg=bg, pady=5)
        row.pack(fill="x")

        desc = snippet.get("description", "")
        cmd = snippet.get("command", "")

        tk.Label(row, text=desc, bg=bg, width=30, anchor="w",
                 wraplength=210, justify="left", padx=8).pack(side="left")
        tk.Label(row, text=cmd, bg=bg, anchor="w",
                 font=("monospace", 9), fg="#222222").pack(
                 side="left", fill="x", expand=True, padx=4)

        btns = tk.Frame(row, bg=bg)
        btns.pack(side="right", padx=6)

        tk.Button(btns, text="Run", width=5, relief="flat",
                  bg="#4CAF50", fg="white", activebackground="#388E3C",
                  command=lambda c=cmd: run_snippet(c)).pack(side="left", padx=2)
        tk.Button(btns, text="Copy", width=5, relief="flat",
                  bg="#2196F3", fg="white", activebackground="#1565C0",
                  command=lambda c=cmd: self._copy(c)).pack(side="left", padx=2)
        tk.Button(btns, text="Edit", width=5, relief="flat",
                  bg="#FF9800", fg="white", activebackground="#E65100",
                  command=lambda i=idx: self._edit(i)).pack(side="left", padx=2)
        tk.Button(btns, text="Del", width=4, relief="flat",
                  bg="#f44336", fg="white", activebackground="#B71C1C",
                  command=lambda i=idx: self._delete(i)).pack(side="left", padx=2)

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def _add(self):
        dlg = SnippetDialog(self.root, title="Add Snippet")
        if dlg.result:
            self.snippets.append(dlg.result)
            save_snippets(self.snippets)
            self._render()

    def _edit(self, idx):
        s = self.snippets[idx]
        dlg = SnippetDialog(self.root, title="Edit Snippet",
                            command=s["command"],
                            description=s.get("description", ""))
        if dlg.result:
            self.snippets[idx] = dlg.result
            save_snippets(self.snippets)
            self._render()

    def _delete(self, idx):
        name = self.snippets[idx].get("description") or self.snippets[idx]["command"]
        if messagebox.askyesno("Confirm Delete", f"Delete snippet:\n{name!r}?", parent=self.root):
            self.snippets.pop(idx)
            save_snippets(self.snippets)
            self._render()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()


# ── App entry point ─────────────────────────────────────────────────────────────

class SnippetTrayApp:
    def __init__(self):
        self.root = tk.Tk()
        self.window = MainWindow(self.root)
        self.icon = self._create_tray_icon()

    def _create_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open SnippetTray", self._open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        return pystray.Icon("snippettray", _make_icon_image(), "SnippetTray", menu)

    def _open(self, *_):
        self.root.after(0, self.window.show)

    def _quit(self, *_):
        self.icon.stop()
        self.root.after(0, self.root.quit)

    def run(self):
        self.root.withdraw()
        threading.Thread(target=self.icon.run, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    SnippetTrayApp().run()
