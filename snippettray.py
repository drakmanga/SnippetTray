#!/usr/bin/env python3
# External dependencies: pystray, Pillow, PyQt6  (pip install pystray Pillow PyQt6)

import json
import os
import shlex
import subprocess
import sys
import threading
from pathlib import Path

if os.environ.get("WAYLAND_DISPLAY") and "PYSTRAY_BACKEND" not in os.environ:
    os.environ["PYSTRAY_BACKEND"] = "appindicator"

import pystray
from PIL import Image, ImageDraw

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)


CONFIG_DIR = Path.home() / ".config" / "snippettray"
SNIPPETS_FILE = CONFIG_DIR / "snippets.json"

DEFAULT_SNIPPETS = [
    {"command": "apt update && apt upgrade -y", "description": "Update system packages (Debian/Ubuntu)"},
    {"command": "journalctl -xe --no-pager | tail -100", "description": "View recent system log entries"},
    {"command": "df -h && echo && free -h", "description": "Check disk and memory usage"},
]

_QSS = """
QPushButton {
    border-radius: 4px;
    padding: 4px 10px;
}
QPushButton#runButton   { background: #43A047; color: #fff; border: none; }
QPushButton#runButton:hover   { background: #388E3C; }
QPushButton#runButton:pressed { background: #2E7D32; }

QPushButton#copyButton   { background: #1E88E5; color: #fff; border: none; }
QPushButton#copyButton:hover   { background: #1565C0; }
QPushButton#copyButton:pressed { background: #0D47A1; }

QPushButton#editButton   { background: #FB8C00; color: #fff; border: none; }
QPushButton#editButton:hover   { background: #E65100; }
QPushButton#editButton:pressed { background: #BF360C; }

QPushButton#deleteButton   { background: #E53935; color: #fff; border: none; }
QPushButton#deleteButton:hover   { background: #C62828; }
QPushButton#deleteButton:pressed { background: #B71C1C; }

QPushButton#addButton {
    background: #43A047; color: #fff; border: none;
    padding: 6px 14px; border-radius: 4px;
}
QPushButton#addButton:hover   { background: #388E3C; }
QPushButton#addButton:pressed { background: #2E7D32; }

QPushButton#saveButton {
    background: #43A047; color: #fff; border: none;
    padding: 6px 18px; border-radius: 4px;
}
QPushButton#saveButton:hover   { background: #388E3C; }
QPushButton#saveButton:pressed { background: #2E7D32; }

QPushButton#cancelButton {
    padding: 6px 18px; border-radius: 4px;
}
QPushButton#cancelButton:hover   { background: palette(mid); }
QPushButton#cancelButton:pressed { background: palette(dark); }
"""


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

def _has_exe(name: str) -> bool:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return True
    return False


def _build_terminal_cmd(shell_script):
    if _has_exe("konsole"):
        return ["konsole", "-e", "bash", "-c", shell_script]
    if _has_exe("gnome-terminal"):
        return ["gnome-terminal", "--", "bash", "-c", shell_script]
    if _has_exe("xfce4-terminal"):
        return ["xfce4-terminal", "-e", "bash -c " + shlex.quote(shell_script)]
    if _has_exe("xterm"):
        return ["xterm", "-e", "bash", "-c", shell_script]
    return None


def run_snippet(command, keep_open=False, use_sudo=True, working_dir=""):
    shell_script = f"sudo {command}" if use_sudo else command
    if working_dir:
        shell_script = f"cd {shlex.quote(os.path.expanduser(working_dir))} && {shell_script}"
    if keep_open:
        shell_script += "\nread -rp 'Press Enter to close...'"
    args = _build_terminal_cmd(shell_script)
    if args is None:
        QMessageBox.critical(
            None, "No Terminal Found",
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


# ── Thread bridge ───────────────────────────────────────────────────────────────

class _Bridge(QObject):
    show_requested = pyqtSignal()


# ── Snippet dialog ──────────────────────────────────────────────────────────────

class SnippetDialog(QDialog):
    def __init__(self, parent=None, *, title="Snippet", command="", description="",
                 keep_open=False, use_sudo=True, working_dir=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(560)
        self.result_data = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._desc = QLineEdit(description)
        self._desc.setPlaceholderText("e.g. Update system packages")
        form.addRow("Description:", self._desc)

        self._wdir = QLineEdit(working_dir)
        self._wdir.setFont(QFont("monospace", 10))
        self._wdir.setPlaceholderText("~/projects/myapp  (leave empty for default)")
        form.addRow("Working Dir:", self._wdir)

        self._cmd = QLineEdit(command)
        self._cmd.setFont(QFont("monospace", 10))
        self._cmd.setPlaceholderText("e.g. apt update && apt upgrade -y")
        form.addRow("Command:", self._cmd)

        layout.addLayout(form)

        self._sudo = QCheckBox("Run with sudo (as root)")
        self._sudo.setChecked(use_sudo)
        layout.addWidget(self._sudo)

        self._keep = QCheckBox("Keep terminal open after command finishes")
        self._keep.setChecked(keep_open)
        layout.addWidget(self._keep)

        layout.addSpacing(4)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("saveButton")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        QShortcut(QKeySequence("Escape"), self, self.reject)

    def _save(self):
        cmd = self._cmd.text().strip()
        if not cmd:
            QMessageBox.warning(self, "Validation", "Command cannot be empty.")
            return
        self.result_data = {
            "command": cmd,
            "description": self._desc.text().strip(),
            "working_dir": self._wdir.text().strip(),
            "use_sudo": self._sudo.isChecked(),
            "keep_open": self._keep.isChecked(),
        }
        self.accept()


# ── Main window ─────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.snippets = load_snippets()
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("SnippetTray")
        self.setMinimumSize(720, 440)
        self.resize(960, 580)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──
        toolbar = QWidget()
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(16, 10, 16, 10)
        title_lbl = QLabel("SnippetTray")
        title_lbl.setFont(QFont("", 14, QFont.Weight.Bold))
        tb.addWidget(title_lbl)
        tb.addStretch()
        add_btn = QPushButton("+ Add Snippet")
        add_btn.setObjectName("addButton")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self._add)
        tb.addWidget(add_btn)
        root.addWidget(toolbar)

        _sep(root)

        # ── Column headers ──
        hdr = QWidget()
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(16, 5, 16, 5)
        bold9 = QFont("", 9, QFont.Weight.Bold)
        lbl_d = QLabel("Description")
        lbl_d.setFont(bold9)
        lbl_d.setFixedWidth(220)
        hdr_layout.addWidget(lbl_d)
        lbl_c = QLabel("Command")
        lbl_c.setFont(bold9)
        hdr_layout.addWidget(lbl_c, stretch=1)
        lbl_a = QLabel("Actions")
        lbl_a.setFont(bold9)
        lbl_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_a.setFixedWidth(236)
        hdr_layout.addWidget(lbl_a)
        root.addWidget(hdr)

        _sep(root)

        # ── Scrollable snippet list ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll, stretch=1)

        self._render()

    def _render(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.snippets:
            empty = QLabel("No snippets yet.\nClick '+ Add Snippet' to create one.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: gray; font-size: 13px;")
            empty.setMinimumHeight(140)
            self._list_layout.insertWidget(0, empty)
            return

        alt_color = QApplication.palette().color(QPalette.ColorRole.AlternateBase)

        for idx, snippet in enumerate(self.snippets):
            row = self._make_row(idx, snippet)
            if idx % 2 == 1:
                row.setAutoFillBackground(True)
                p = row.palette()
                p.setColor(QPalette.ColorRole.Window, alt_color)
                row.setPalette(p)
            self._list_layout.insertWidget(idx, row)

    def _make_row(self, idx, snippet):
        desc = snippet.get("description", "")
        cmd = snippet.get("command", "")
        keep = snippet.get("keep_open", False)
        sudo = snippet.get("use_sudo", True)
        wdir = snippet.get("working_dir", "")

        container = QFrame()
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        content = QWidget()
        hl = QHBoxLayout(content)
        hl.setContentsMargins(16, 8, 16, 8)
        hl.setSpacing(8)

        desc_lbl = QLabel(desc or "(no description)")
        desc_lbl.setWordWrap(True)
        desc_lbl.setFixedWidth(220)
        if not desc:
            desc_lbl.setStyleSheet("color: gray;")
        hl.addWidget(desc_lbl)

        cmd_lbl = QLabel(cmd)
        cmd_lbl.setFont(QFont("monospace", 9))
        cmd_lbl.setWordWrap(True)
        cmd_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        hl.addWidget(cmd_lbl, stretch=1)

        btns_widget = QWidget()
        btns_widget.setFixedWidth(236)
        btns = QHBoxLayout(btns_widget)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(4)

        run_btn = QPushButton("Run")
        run_btn.setObjectName("runButton")
        run_btn.setFixedWidth(54)
        run_btn.clicked.connect(lambda _, c=cmd, k=keep, s=sudo, w=wdir: run_snippet(c, k, s, w))
        btns.addWidget(run_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("copyButton")
        copy_btn.setFixedWidth(54)
        copy_btn.clicked.connect(lambda _, c=cmd: self._copy(c))
        btns.addWidget(copy_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("editButton")
        edit_btn.setFixedWidth(54)
        edit_btn.clicked.connect(lambda _, i=idx: self._edit(i))
        btns.addWidget(edit_btn)

        del_btn = QPushButton("Del")
        del_btn.setObjectName("deleteButton")
        del_btn.setFixedWidth(46)
        del_btn.clicked.connect(lambda _, i=idx: self._delete(i))
        btns.addWidget(del_btn)

        hl.addWidget(btns_widget)
        vl.addWidget(content)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        vl.addWidget(sep)

        return container

    def _copy(self, text):
        QApplication.clipboard().setText(text)

    def _add(self):
        dlg = SnippetDialog(self, title="Add Snippet")
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            self.snippets.append(dlg.result_data)
            save_snippets(self.snippets)
            self._render()

    def _edit(self, idx):
        s = self.snippets[idx]
        dlg = SnippetDialog(
            self, title="Edit Snippet",
            command=s["command"],
            description=s.get("description", ""),
            working_dir=s.get("working_dir", ""),
            use_sudo=bool(s.get("use_sudo", True)),
            keep_open=bool(s.get("keep_open", False)),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_data:
            self.snippets[idx] = dlg.result_data
            save_snippets(self.snippets)
            self._render()

    def _delete(self, idx):
        name = self.snippets[idx].get("description") or self.snippets[idx]["command"]
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirm Delete")
        msg.setText(f"Delete snippet:\n{name!r}?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.button(QMessageBox.StandardButton.Yes).setStyleSheet(
            "QPushButton{background:#E53935;color:#fff;border:none;border-radius:4px;padding:6px 18px;}"
            "QPushButton:hover{background:#C62828;}"
            "QPushButton:pressed{background:#B71C1C;}"
        )
        msg.button(QMessageBox.StandardButton.No).setStyleSheet(
            "QPushButton{border-radius:4px;padding:6px 18px;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:pressed{background:palette(dark);}"
        )
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.snippets.pop(idx)
            save_snippets(self.snippets)
            self._render()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


def _sep(layout: QVBoxLayout):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    layout.addWidget(line)


# ── App entry point ─────────────────────────────────────────────────────────────

class SnippetTrayApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.window = MainWindow()
        self.bridge = _Bridge()
        self.bridge.show_requested.connect(self.window.show_and_raise)
        self.icon = self._create_tray_icon()

    def _create_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open SnippetTray", self._open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        return pystray.Icon("snippettray", _make_icon_image(), "SnippetTray", menu)

    def _open(self, icon=None, item=None):
        self.bridge.show_requested.emit()

    def _quit(self, icon=None, item=None):
        self.icon.stop()
        self.app.quit()

    def run(self):
        threading.Thread(target=self.icon.run, daemon=True).start()
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SnippetTray")
    app.setStyle("Fusion")
    app.setStyleSheet(_QSS)
    SnippetTrayApp(app).run()
