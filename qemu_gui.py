"""
QEMU GUI - VirtualBox-Style VM Manager
Manage QEMU virtual machines with a familiar VirtualBox-like interface.
Features: auto-detect OS from ISO, smart presets, incompatibility prevention.
"""

import sys
import subprocess
import json
import os
import re
import uuid
import math
import platform
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QCheckBox, QTextEdit,
    QGroupBox, QFileDialog, QMessageBox, QScrollArea, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QSplitter, QToolBar, QStatusBar, QFrame,
    QStackedWidget, QSizePolicy, QFormLayout, QGridLayout, QMenu, QInputDialog,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QProcess, QSize, Signal, QTimer, QPoint
from PySide6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QAction, QPen, QBrush,
    QPalette, QLinearGradient, QPolygon
)

PROFILES_DIR = Path.home() / ".qemu-gui" / "machines"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
QEMU_PATH = r"C:\Program Files\qemu"
HOST_OS = platform.system()

# === OS DETECTION ===
ISO_PATTERNS = [
    (r"(?i)win.*11|w11",                          "Windows 11"),
    (r"(?i)win.*10|w10",                          "Windows 10"),
    (r"(?i)win.*(8\.1|8_1)",                      "Windows 8.1"),
    (r"(?i)win.*8|w8",                            "Windows 8"),
    (r"(?i)win.*7|w7",                            "Windows 7"),
    (r"(?i)win.*(xp|2k|2000|2003|2008)",          "Windows XP/Legacy"),
    (r"(?i)win.*server.*2022",                    "Windows Server 2022"),
    (r"(?i)win.*server.*2019",                    "Windows Server 2019"),
    (r"(?i)win.*server",                          "Windows Server"),
    (r"(?i)windows",                              "Windows 10"),
    (r"(?i)ubuntu.*24",                           "Ubuntu 24"),
    (r"(?i)ubuntu.*22",                           "Ubuntu 22"),
    (r"(?i)ubuntu",                               "Ubuntu"),
    (r"(?i)debian.*12",                           "Debian 12"),
    (r"(?i)debian",                               "Debian"),
    (r"(?i)fedora",                               "Fedora"),
    (r"(?i)arch",                                 "Arch Linux"),
    (r"(?i)mint",                                 "Linux Mint"),
    (r"(?i)manjaro",                              "Manjaro"),
    (r"(?i)pop[_-]?os",                           "Pop!_OS"),
    (r"(?i)opensuse|suse",                        "openSUSE"),
    (r"(?i)centos|rocky|alma",                    "CentOS/RHEL"),
    (r"(?i)rhel|red.*hat",                        "CentOS/RHEL"),
    (r"(?i)kali",                                 "Kali Linux"),
    (r"(?i)tails",                                "Tails"),
    (r"(?i)gentoo",                               "Gentoo"),
    (r"(?i)slackware",                            "Slackware"),
    (r"(?i)void",                                 "Void Linux"),
    (r"(?i)alpine",                               "Alpine Linux"),
    (r"(?i)nixos",                                "NixOS"),
    (r"(?i)linux|gnu",                            "Linux Generic"),
    (r"(?i)sonoma",                               "macOS Sonoma"),
    (r"(?i)ventura",                              "macOS Ventura"),
    (r"(?i)monterey",                             "macOS Monterey"),
    (r"(?i)big.*sur",                             "macOS Big Sur"),
    (r"(?i)catalina",                             "macOS Catalina"),
    (r"(?i)mojave",                               "macOS Mojave"),
    (r"(?i)high.*sierra",                         "macOS High Sierra"),
    (r"(?i)sierra",                               "macOS Sierra"),
    (r"(?i)el.*capitan",                          "macOS El Capitan"),
    (r"(?i)yosemite",                             "macOS Yosemite"),
    (r"(?i)mavericks",                            "macOS Mavericks"),
    (r"(?i)mountain.*lion",                       "macOS Mountain Lion"),
    (r"(?i)lion(?!.*mountain)",                   "macOS Lion"),
    (r"(?i)snow.*leopard",                        "macOS Snow Leopard"),
    (r"(?i)leopard",                              "macOS Leopard"),
    (r"(?i)tiger",                                "macOS Tiger"),
    (r"(?i)mac.*os|osx|os.*x|darwin|macos",       "macOS Generic"),
    (r"(?i)freebsd",                              "FreeBSD"),
    (r"(?i)openbsd",                              "OpenBSD"),
    (r"(?i)netbsd",                               "NetBSD"),
    (r"(?i)dragonfly",                            "DragonFly BSD"),
    (r"(?i)solaris|illumos|openindiana",          "Solaris"),
    (r"(?i)reactos",                              "ReactOS"),
    (r"(?i)haiku",                                "Haiku"),
    (r"(?i)freedos",                              "FreeDOS"),
    (r"(?i)kolibri",                              "KolibriOS"),
    (r"(?i)temple",                               "TempleOS"),
]

def detect_os_from_iso(filepath):
    name = os.path.basename(filepath)
    for pattern, os_key in ISO_PATTERNS:
        if re.search(pattern, name):
            return os_key
    return None

def os_key_to_type(os_key):
    if not os_key: return "Other"
    k = os_key.lower()
    if "windows" in k or k == "reactos": return "Windows"
    if any(x in k for x in ("ubuntu","debian","fedora","arch","mint","manjaro","pop","suse",
           "centos","rhel","kali","tails","gentoo","slackware","void","alpine","nixos","linux")):
        return "Linux"
    if "mac" in k or "darwin" in k: return "macOS"
    if "bsd" in k or "dragonfly" in k: return "BSD"
    if "solaris" in k or "illumos" in k: return "Solaris"
    return "Other"

# === OS PRESETS ===
_WIN_MODERN = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 2, "threads": 2, "sockets": 1, "memory": 4096},
    "display_sound": {"graphics": "qxl", "display": "gtk", "fullscreen": False, "sound_card": "hda", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"whpx": True, "usb_enabled": True, "usb_type": "usb-xhci", "bios": "UEFI (OVMF)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_WIN_LEGACY = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 2, "threads": 1, "sockets": 1, "memory": 2048},
    "display_sound": {"graphics": "cirrus", "display": "gtk", "fullscreen": False, "sound_card": "ac97", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "rtl8139"},
    "misc": {"whpx": True, "usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_LINUX_MODERN = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 2, "threads": 2, "sockets": 1, "memory": 2048},
    "display_sound": {"graphics": "virtio", "display": "gtk", "fullscreen": False, "sound_card": "intel-hda", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "virtio-net"},
    "misc": {"whpx": True, "usb_enabled": True, "usb_type": "usb-xhci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_LINUX_LIGHT = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 1, "threads": 1, "sockets": 1, "memory": 1024},
    "display_sound": {"graphics": "std", "display": "gtk", "fullscreen": False, "sound_card": "intel-hda", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "virtio-net"},
    "misc": {"whpx": True, "usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_MACOS_PRESET = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "Penryn", "cores": 2, "threads": 2, "sockets": 1, "memory": 4096},
    "display_sound": {"graphics": "vmware", "display": "gtk", "fullscreen": False, "sound_card": "intel-hda", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"usb_enabled": True, "usb_type": "usb-xhci", "bios": "UEFI (OVMF)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_MACOS_PPC = {
    "cpu_mem": {"architecture": "ppc", "cpu_model": "G4", "cores": 1, "threads": 1, "sockets": 1, "memory": 512},
    "display_sound": {"graphics": "std", "display": "gtk", "fullscreen": False, "sound_card": "none", "audio_driver": "none"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_BSD_PRESET = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 2, "threads": 1, "sockets": 1, "memory": 1024},
    "display_sound": {"graphics": "std", "display": "gtk", "fullscreen": False, "sound_card": "intel-hda", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"whpx": True, "usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}
_OTHER = {
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 1, "threads": 1, "sockets": 1, "memory": 512},
    "display_sound": {"graphics": "std", "display": "gtk", "fullscreen": False, "sound_card": "none", "audio_driver": "none"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)"},
    "storage": {"boot": "CD-ROM (d)"},
}

def _mp(base, **overrides):
    """Merge preset helper - deep-ish copy with cpu_mem overrides."""
    r = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in overrides.items():
        if k in r and isinstance(r[k], dict) and isinstance(v, dict):
            r[k] = {**r[k], **v}
        else:
            r[k] = v
    return r

OS_PRESETS = {
    "Windows 11":          _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 4096}),
    "Windows 10":          _WIN_MODERN,
    "Windows 8.1":         _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 2048}),
    "Windows 8":           _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 2048}),
    "Windows 7":           _mp(_WIN_LEGACY, cpu_mem={**_WIN_LEGACY["cpu_mem"], "memory": 2048},
                               display_sound={**_WIN_LEGACY["display_sound"], "graphics": "std"}),
    "Windows XP/Legacy":   _mp(_WIN_LEGACY, cpu_mem={**_WIN_LEGACY["cpu_mem"], "memory": 512}),
    "Windows Server 2022": _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 4096, "cores": 4}),
    "Windows Server 2019": _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 4096, "cores": 4}),
    "Windows Server":      _mp(_WIN_MODERN, cpu_mem={**_WIN_MODERN["cpu_mem"], "memory": 4096, "cores": 4}),
    "Ubuntu 24":           _mp(_LINUX_MODERN, cpu_mem={**_LINUX_MODERN["cpu_mem"], "memory": 4096}),
    "Ubuntu 22":           _LINUX_MODERN,
    "Ubuntu":              _LINUX_MODERN,
    "Debian 12":           _LINUX_MODERN,
    "Debian":              _LINUX_MODERN,
    "Fedora":              _LINUX_MODERN,
    "Arch Linux":          _LINUX_MODERN,
    "Linux Mint":          _LINUX_MODERN,
    "Manjaro":             _LINUX_MODERN,
    "Pop!_OS":             _LINUX_MODERN,
    "openSUSE":            _LINUX_MODERN,
    "CentOS/RHEL":         _mp(_LINUX_MODERN, cpu_mem={**_LINUX_MODERN["cpu_mem"], "memory": 4096, "cores": 4}),
    "Kali Linux":          _LINUX_MODERN,
    "Tails":               _mp(_LINUX_MODERN, cpu_mem={**_LINUX_MODERN["cpu_mem"], "memory": 2048}),
    "Gentoo":              _LINUX_MODERN,
    "Slackware":           _LINUX_LIGHT,
    "Void Linux":          _LINUX_LIGHT,
    "Alpine Linux":        _mp(_LINUX_LIGHT, cpu_mem={**_LINUX_LIGHT["cpu_mem"], "memory": 512}),
    "NixOS":               _LINUX_MODERN,
    "Linux Generic":       _LINUX_MODERN,
    "macOS Sonoma":        _mp(_MACOS_PRESET, cpu_mem={**_MACOS_PRESET["cpu_mem"], "memory": 8192}),
    "macOS Ventura":       _mp(_MACOS_PRESET, cpu_mem={**_MACOS_PRESET["cpu_mem"], "memory": 8192}),
    "macOS Monterey":      _mp(_MACOS_PRESET, cpu_mem={**_MACOS_PRESET["cpu_mem"], "memory": 8192}),
    "macOS Big Sur":       _mp(_MACOS_PRESET, cpu_mem={**_MACOS_PRESET["cpu_mem"], "memory": 8192}),
    "macOS Catalina":      _MACOS_PRESET,
    "macOS Mojave":        _MACOS_PRESET,
    "macOS High Sierra":   _MACOS_PRESET,
    "macOS Sierra":        _MACOS_PRESET,
    "macOS El Capitan":    _MACOS_PRESET,
    "macOS Yosemite":      _MACOS_PRESET,
    "macOS Mavericks":     _MACOS_PRESET,
    "macOS Mountain Lion":  _MACOS_PRESET,
    "macOS Lion":          _MACOS_PRESET,
    "macOS Snow Leopard":  _MACOS_PRESET,
    "macOS Leopard":       _MACOS_PPC,
    "macOS Tiger":         _MACOS_PPC,
    "macOS Generic":       _MACOS_PRESET,
    "FreeBSD":             _BSD_PRESET,
    "OpenBSD":             _mp(_BSD_PRESET, cpu_mem={**_BSD_PRESET["cpu_mem"], "memory": 512}),
    "NetBSD":              _mp(_BSD_PRESET, cpu_mem={**_BSD_PRESET["cpu_mem"], "memory": 512}),
    "DragonFly BSD":       _BSD_PRESET,
    "Solaris":             _mp(_OTHER, cpu_mem={**_OTHER["cpu_mem"], "memory": 2048, "cores": 2}),
    "ReactOS":             _mp(_WIN_LEGACY, cpu_mem={**_WIN_LEGACY["cpu_mem"], "memory": 512}),
    "Haiku":               _OTHER,
    "FreeDOS":             _mp(_OTHER, cpu_mem={"architecture": "i386", "cpu_model": "host", "cores": 1, "threads": 1, "sockets": 1, "memory": 64}),
    "KolibriOS":           _mp(_OTHER, cpu_mem={"architecture": "i386", "cpu_model": "host", "cores": 1, "threads": 1, "sockets": 1, "memory": 128}),
    "TempleOS":            _mp(_OTHER, cpu_mem={**_OTHER["cpu_mem"], "memory": 512}),
}

DEFAULT_PROFILE = {
    "name": "New VM", "os_type": "Other", "detected_os": "",
    "cpu_mem": {"architecture": "x86_64", "cpu_model": "host", "cores": 2, "threads": 1, "sockets": 1, "memory": 2048},
    "storage": {"hda": "", "hdb": "", "cdrom": "", "boot": "Hard Disk (c)"},
    "display_sound": {"graphics": "std", "display": "gtk", "fullscreen": False, "sound_card": "none", "audio_driver": "dsound"},
    "network": {"mode": "User Mode (NAT)", "nic": "e1000"},
    "misc": {"kvm": False, "whpx": False, "hax": False, "usb_enabled": True, "usb_type": "usb-ehci", "bios": "Default (SeaBIOS)", "extra_args": ""},
}

def _apply_host_accel(profile):
    misc = profile.setdefault("misc", {})
    if HOST_OS == "Windows":
        misc["kvm"] = False
    elif HOST_OS == "Linux":
        misc["whpx"] = False; misc["hax"] = False; misc["kvm"] = True
    elif HOST_OS == "Darwin":
        misc["kvm"] = False; misc["whpx"] = False; misc["hax"] = True
    else:
        misc["kvm"] = False; misc["whpx"] = False; misc["hax"] = False

def build_preset_profile(os_key, iso_path=""):
    base = json.loads(json.dumps(DEFAULT_PROFILE))
    base["name"] = os_key or "New VM"
    base["os_type"] = os_key_to_type(os_key)
    base["detected_os"] = os_key or ""
    if iso_path:
        base["storage"]["cdrom"] = iso_path
        base["storage"]["boot"] = "CD-ROM (d)"
    preset = OS_PRESETS.get(os_key)
    if preset:
        for section, values in preset.items():
            if section in base and isinstance(values, dict):
                base[section].update(values)
    _apply_host_accel(base)
    return base

# === COMPATIBILITY ENGINE ===
ARCH_GRAPHICS = {
    "x86_64": ["std","cirrus","vmware","qxl","virtio","none"], "i386": ["std","cirrus","vmware","qxl","virtio","none"],
    "arm": ["std","virtio","none"], "aarch64": ["std","virtio","none"],
    "ppc": ["std","none"], "ppc64": ["std","none"],
    "mips": ["std","cirrus","none"], "mips64": ["std","cirrus","none"],
    "riscv32": ["std","virtio","none"], "riscv64": ["std","virtio","none"],
    "sparc": ["std","none"], "sparc64": ["std","none"],
}
UEFI_ARCHS = {"x86_64", "i386", "aarch64"}
ARCH_NICS = {
    "x86_64": ["e1000","virtio-net","rtl8139","ne2k_pci","i82557b"], "i386": ["e1000","virtio-net","rtl8139","ne2k_pci","i82557b"],
    "arm": ["virtio-net","e1000"], "aarch64": ["virtio-net","e1000"],
    "ppc": ["e1000","virtio-net"], "ppc64": ["e1000","virtio-net"],
    "mips": ["e1000","virtio-net"], "mips64": ["e1000","virtio-net"],
    "riscv32": ["virtio-net"], "riscv64": ["virtio-net"],
    "sparc": ["e1000"], "sparc64": ["e1000"],
}
HOST_ACCEL = {"Windows": {"whpx","hax"}, "Linux": {"kvm","hax"}, "Darwin": {"hax"}}

def get_valid_graphics(arch): return ARCH_GRAPHICS.get(arch, ["std","none"])
def get_valid_nics(arch): return ARCH_NICS.get(arch, ["e1000"])
def can_use_uefi(arch): return arch in UEFI_ARCHS
def get_available_accels(): return HOST_ACCEL.get(HOST_OS, set())

# === ICONS ===
OS_COLORS = {"Windows": "#0078D4", "Linux": "#E95420", "macOS": "#A2AAAD", "BSD": "#AB2B28", "Solaris": "#E97826", "Other": "#6C757D"}
OS_LABELS = list(OS_COLORS.keys())

def make_os_icon(os_type, size=64):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    color = QColor(OS_COLORS.get(os_type, "#6C757D"))
    p.setBrush(QBrush(color)); p.setPen(QPen(color.darker(130), 2))
    p.drawEllipse(4, 4, size-8, size-8)
    p.setPen(QPen(Qt.white)); p.setFont(QFont("Segoe UI", size//3, QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, os_type[0] if os_type else "?")
    p.end(); return QIcon(pm)

def make_toolbar_icon(icon_type, color="#4A6484"):
    size = 28; pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    c = QColor(color); p.setPen(QPen(c, 2.0)); p.setBrush(Qt.NoBrush)
    if icon_type == "new":
        p.drawRoundedRect(4,5,20,14,2,2); p.drawLine(14,19,14,23); p.drawLine(10,23,18,23)
        p.setPen(QPen(QColor("#27AE60"),2.5)); p.drawLine(14,8,14,16); p.drawLine(10,12,18,12)
    elif icon_type == "settings":
        p.setPen(QPen(c,2.2)); p.drawEllipse(9,9,10,10)
        for a in range(0,360,45):
            r=math.radians(a); p.drawLine(int(14+5*math.cos(r)),int(14+5*math.sin(r)),int(14+7.5*math.cos(r)),int(14+7.5*math.sin(r)))
    elif icon_type == "start":
        p.setBrush(QBrush(QColor("#27AE60"))); p.setPen(QPen(QColor("#1E8449"),1.5))
        p.drawPolygon(QPolygon([QPoint(9,6),QPoint(23,14),QPoint(9,22)]))
    elif icon_type == "clone":
        p.drawRoundedRect(3,7,14,14,2,2); p.setPen(QPen(c.lighter(130),2.0)); p.drawRoundedRect(9,3,14,14,2,2)
    elif icon_type == "remove":
        p.setPen(QPen(QColor("#C0392B"),2.2)); p.drawEllipse(4,4,20,20); p.drawLine(9,9,19,19); p.drawLine(19,9,9,19)
    elif icon_type == "import":
        p.drawLine(6,22,22,22); p.drawLine(6,16,6,22); p.drawLine(22,16,22,22)
        p.setPen(QPen(QColor("#16A085"),2.5)); p.drawLine(14,4,14,17); p.drawLine(10,13,14,17); p.drawLine(18,13,14,17)
    elif icon_type == "export":
        p.drawLine(6,22,22,22); p.drawLine(6,16,6,22); p.drawLine(22,16,22,22)
        p.setPen(QPen(QColor("#2C3E50"),2.5)); p.drawLine(14,17,14,4); p.drawLine(10,8,14,4); p.drawLine(18,8,14,4)
    else:
        p.setPen(QColor(color)); p.setFont(QFont("Segoe UI",14,QFont.Bold)); p.drawText(pm.rect(),Qt.AlignCenter,icon_type[0].upper())
    p.end(); return QIcon(pm)

# === PROFILE MANAGER ===
class ProfileManager:
    @staticmethod
    def list_profiles():
        r = []
        for f in PROFILES_DIR.glob("*.json"):
            try: r.append((f.stem, json.loads(f.read_text())))
            except: pass
        r.sort(key=lambda x: x[1].get("name","").lower()); return r
    @staticmethod
    def load(uid):
        p = PROFILES_DIR / f"{uid}.json"
        return json.loads(p.read_text()) if p.exists() else None
    @staticmethod
    def save(uid, data): (PROFILES_DIR / f"{uid}.json").write_text(json.dumps(data, indent=2))
    @staticmethod
    def delete(uid):
        p = PROFILES_DIR / f"{uid}.json"
        if p.exists(): p.unlink()
    @staticmethod
    def new_uid(): return uuid.uuid4().hex[:12]

# === STYLESHEET ===
STYLESHEET = """
QMainWindow, QDialog { background-color: #F0F0F0; }
QWidget { color: #2C3E50; }
QToolBar { background: qlineargradient(y1:0,y2:1,stop:0 #E8EEF4,stop:0.5 #D6DFEB,stop:1 #C4D0DE); border-bottom: 1px solid #A0A8B4; spacing: 4px; padding: 4px 8px; }
QToolBar QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px 10px 3px 10px; font-size: 11px; font-weight: 600; color: #2C3E50; min-width: 56px; }
QToolBar QToolButton:hover { background: qlineargradient(y1:0,y2:1,stop:0 #F8FAFC,stop:1 #E0E8F0); border: 1px solid #9DB4CC; }
QToolBar QToolButton:pressed { background: qlineargradient(y1:0,y2:1,stop:0 #C8D4E2,stop:1 #B0C0D4); }
QToolBar QToolButton:disabled { color: #A0A8B0; }
QToolBar::separator { width: 1px; background: #B0B8C4; margin: 6px 6px; }
QListWidget#vmList { background: white; border: 1px solid #B8C0CC; outline: none; font-size: 13px; }
QListWidget#vmList::item { padding: 10px 8px; border-bottom: 1px solid #E8E8E8; }
QListWidget#vmList::item:selected { background: qlineargradient(y1:0,y2:1,stop:0 #3A7BD5,stop:1 #2B6CC4); color: white; }
QListWidget#vmList::item:hover:!selected { background: #EBF0F7; }
QFrame#detailPanel { background: white; border: 1px solid #B8C0CC; }
QGroupBox { font-weight: 600; font-size: 12px; color: #2C3E50; border: 1px solid #C8D0DA; border-radius: 4px; margin-top: 14px; padding-top: 18px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QTabWidget::pane { border: 1px solid #B8C0CC; background: white; }
QTabBar::tab { background: qlineargradient(y1:0,y2:1,stop:0 #F0F4F8,stop:1 #D8E0EA); border: 1px solid #B8C0CC; border-bottom: none; padding: 8px 18px; font-size: 12px; min-width: 80px; }
QTabBar::tab:selected { background: white; border-bottom: 1px solid white; font-weight: 600; }
QTabBar::tab:hover:!selected { background: #E4EAF2; }
QPushButton { background: qlineargradient(y1:0,y2:1,stop:0 #FAFBFC,stop:1 #E8ECF0); border: 1px solid #B0B8C4; border-radius: 4px; padding: 6px 16px; font-size: 12px; color: #2C3E50; min-height: 22px; }
QPushButton:hover { background: qlineargradient(y1:0,y2:1,stop:0 #FFF,stop:1 #F0F4F8); border-color: #8899AA; }
QPushButton:pressed { background: #D4DCE8; }
QPushButton:disabled { color: #A0A8B0; background: #F0F0F0; }
QLineEdit, QSpinBox, QComboBox { border: 1px solid #B8C0CC; border-radius: 3px; padding: 5px 8px; background: white; color: #1A1A2E; font-size: 12px; min-height: 22px; selection-background-color: #3A7BD5; selection-color: white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #3A7BD5; }
QComboBox::drop-down { border-left: 1px solid #C8D0DA; width: 24px; }
QComboBox QAbstractItemView { background: white; color: #1A1A2E; selection-background-color: #3A7BD5; selection-color: white; border: 1px solid #B8C0CC; }
QLabel { color: #2C3E50; background: transparent; }
QCheckBox { color: #2C3E50; font-size: 12px; spacing: 6px; }
QTextEdit { border: 1px solid #B8C0CC; border-radius: 3px; font-family: Consolas, monospace; font-size: 11px; color: #1A1A2E; background: #FAFAFA; }
QScrollArea { border: none; }
QStatusBar { background: #E8ECF0; border-top: 1px solid #B8C0CC; font-size: 11px; color: #5A6A7A; }
QSplitter::handle:horizontal { width: 3px; background: #C0C8D4; }
QLabel#detectedBanner { background: #EBF5FB; border: 1px solid #AED6F1; border-radius: 4px; padding: 8px 12px; color: #1A5276; font-size: 12px; }
QLabel#warningBanner { background: #FEF9E7; border: 1px solid #F9E79F; border-radius: 4px; padding: 6px 10px; color: #7D6608; font-size: 11px; }
"""

# === CREATE DISK DIALOG ===
class CreateDiskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Create New Disk Image"); self.setMinimumWidth(500)
        layout = QVBoxLayout()
        pg = QGroupBox("Disk Image Location"); pl = QVBoxLayout(); fl = QHBoxLayout()
        fl.addWidget(QLabel("Save As:")); self.file_path = QLineEdit(); fl.addWidget(self.file_path)
        b = QPushButton("Browse..."); b.clicked.connect(self.browse_save_location); fl.addWidget(b)
        pl.addLayout(fl); pg.setLayout(pl)
        fg = QGroupBox("Disk Format"); fml = QVBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["qcow2 (QEMU Copy-On-Write - Recommended)","raw (Raw Disk Image)","vdi (VirtualBox Disk Image)","vmdk (VMware Disk)","vhdx (Hyper-V Disk)"])
        fml.addWidget(self.format_combo); fg.setLayout(fml)
        sg = QGroupBox("Disk Size"); sl = QHBoxLayout(); sl.addWidget(QLabel("Size:"))
        self.disk_size = QSpinBox(); self.disk_size.setRange(1,2048); self.disk_size.setValue(20)
        sl.addWidget(self.disk_size); sl.addWidget(QLabel("GB")); sl.addStretch(); sg.setLayout(sl)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.create_disk); bbox.rejected.connect(self.reject)
        layout.addWidget(pg); layout.addWidget(fg); layout.addWidget(sg); layout.addWidget(bbox)
        self.setLayout(layout)
    def browse_save_location(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save Disk Image As", "", "QEMU (*.qcow2);;Raw (*.img *.raw);;VDI (*.vdi);;VMDK (*.vmdk);;VHDX (*.vhdx);;All (*.*)")
        if f: self.file_path.setText(f)
    def get_format_string(self):
        return {"qcow2 (QEMU Copy-On-Write - Recommended)":"qcow2","raw (Raw Disk Image)":"raw","vdi (VirtualBox Disk Image)":"vdi","vmdk (VMware Disk)":"vmdk","vhdx (Hyper-V Disk)":"vhdx"}.get(self.format_combo.currentText(),"qcow2")
    def create_disk(self):
        if not self.file_path.text(): QMessageBox.warning(self,"Error","Please specify a file path."); return
        qemu_img = os.path.join(QEMU_PATH, "qemu-img.exe")
        if not os.path.exists(qemu_img): QMessageBox.critical(self,"Error",f"qemu-img.exe not found at: {qemu_img}"); return
        fmt = self.get_format_string(); sz = self.disk_size.value()
        try:
            r = subprocess.run([qemu_img,"create","-f",fmt,self.file_path.text(),f"{sz}G"], capture_output=True, text=True, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if r.returncode == 0: QMessageBox.information(self,"Success",f"Disk created!\n\n{self.file_path.text()}\n{fmt}, {sz} GB"); self.accept()
            else: QMessageBox.critical(self,"Error",f"Failed:\n{r.stderr}")
        except Exception as e: QMessageBox.critical(self,"Error",str(e))

# === NEW VM DIALOG ===
class NewVMDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Create Virtual Machine"); self.setMinimumWidth(520)
        self._detected_os = None; layout = QVBoxLayout()
        # ISO
        iso_group = QGroupBox("Installation Media"); il = QVBoxLayout()
        iso_row = QHBoxLayout(); iso_row.addWidget(QLabel("ISO Image:"))
        self.iso_edit = QLineEdit(); self.iso_edit.setPlaceholderText("Select an ISO to auto-detect OS and recommended settings...")
        self.iso_edit.textChanged.connect(self._on_iso_changed); iso_row.addWidget(self.iso_edit)
        iso_browse = QPushButton("Browse..."); iso_browse.clicked.connect(self._browse_iso); iso_row.addWidget(iso_browse)
        il.addLayout(iso_row)
        self.detect_banner = QLabel(""); self.detect_banner.setObjectName("detectedBanner")
        self.detect_banner.setVisible(False); self.detect_banner.setWordWrap(True); il.addWidget(self.detect_banner)
        iso_group.setLayout(il); layout.addWidget(iso_group)
        # Name
        name_group = QGroupBox("Name and Operating System"); fg = QFormLayout()
        self.name_edit = QLineEdit("New VM"); fg.addRow("Name:", self.name_edit)
        self.os_combo = QComboBox(); self.os_combo.addItems(OS_LABELS); fg.addRow("Type:", self.os_combo)
        name_group.setLayout(fg); layout.addWidget(name_group)
        # Memory
        mem_group = QGroupBox("Memory Size"); ml = QHBoxLayout(); ml.addWidget(QLabel("RAM:"))
        self.mem_spin = QSpinBox(); self.mem_spin.setRange(64,524288); self.mem_spin.setSingleStep(512)
        self.mem_spin.setValue(2048); self.mem_spin.setSuffix(" MB"); ml.addWidget(self.mem_spin); ml.addStretch()
        mem_group.setLayout(ml); layout.addWidget(mem_group)
        # Disk
        disk_group = QGroupBox("Hard Disk"); dl = QVBoxLayout()
        self.no_disk_rb = QCheckBox("Do not add a virtual hard disk"); dl.addWidget(self.no_disk_rb)
        dp = QHBoxLayout(); dp.addWidget(QLabel("Disk Image:")); self.disk_edit = QLineEdit(); dp.addWidget(self.disk_edit)
        b1 = QPushButton("Browse..."); b1.clicked.connect(self._browse_disk); dp.addWidget(b1)
        b2 = QPushButton("Create New..."); b2.clicked.connect(self._create_disk); dp.addWidget(b2)
        dl.addLayout(dp); disk_group.setLayout(dl); layout.addWidget(disk_group)
        layout.addStretch()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._accept); bbox.rejected.connect(self.reject); layout.addWidget(bbox)
        self.setLayout(layout)
    def _browse_iso(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select ISO Image", "", "ISO Images (*.iso);;All (*.*)")
        if f: self.iso_edit.setText(f)
    def _browse_disk(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Disk Image", "", "Disk Images (*.qcow2 *.img *.vdi *.vmdk *.raw);;All (*.*)")
        if f: self.disk_edit.setText(f)
    def _create_disk(self):
        dlg = CreateDiskDialog(self)
        if dlg.exec() == QDialog.Accepted: self.disk_edit.setText(dlg.file_path.text())
    def _on_iso_changed(self, text):
        if not text.strip(): self._detected_os = None; self.detect_banner.setVisible(False); return
        detected = detect_os_from_iso(text); self._detected_os = detected
        if detected:
            os_type = os_key_to_type(detected)
            preset = OS_PRESETS.get(detected, {})
            mem = preset.get("cpu_mem", {}).get("memory", 2048)
            gfx = preset.get("display_sound", {}).get("graphics", "std")
            bios = preset.get("misc", {}).get("bios", "SeaBIOS")
            arch = preset.get("cpu_mem", {}).get("architecture", "x86_64")
            self.detect_banner.setText(f"Detected: {detected}\nRecommended: {arch}, {mem} MB RAM, {gfx} graphics, {bios}")
            self.detect_banner.setVisible(True)
            self.name_edit.setText(detected); self.os_combo.setCurrentText(os_type); self.mem_spin.setValue(mem)
        else:
            self.detect_banner.setText("Could not auto-detect OS from filename. You can set options manually.")
            self.detect_banner.setVisible(True)
    def _accept(self):
        if not self.name_edit.text().strip(): QMessageBox.warning(self,"Error","Please enter a VM name."); return
        self.accept()
    def get_profile(self):
        iso = self.iso_edit.text().strip()
        if self._detected_os: p = build_preset_profile(self._detected_os, iso)
        else:
            p = json.loads(json.dumps(DEFAULT_PROFILE))
            if iso: p["storage"]["cdrom"] = iso; p["storage"]["boot"] = "CD-ROM (d)"
            _apply_host_accel(p)
        p["name"] = self.name_edit.text().strip(); p["os_type"] = self.os_combo.currentText()
        p["cpu_mem"]["memory"] = self.mem_spin.value(); p["detected_os"] = self._detected_os or ""
        if not self.no_disk_rb.isChecked() and self.disk_edit.text(): p["storage"]["hda"] = self.disk_edit.text()
        return p

# === SETTINGS DIALOG ===
class SettingsDialog(QDialog):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Settings \u2014 {profile.get('name','VM')}"); self.setMinimumSize(720,580)
        self.profile = json.loads(json.dumps(profile)); self._updating = False
        layout = QVBoxLayout(); self.tabs = QTabWidget()

        # General
        gen_w = QWidget(); gl = QFormLayout()
        self.name_edit = QLineEdit(self.profile.get("name","")); gl.addRow("Name:", self.name_edit)
        self.os_combo = QComboBox(); self.os_combo.addItems(OS_LABELS)
        self.os_combo.setCurrentText(self.profile.get("os_type","Other")); gl.addRow("OS Type:", self.os_combo)
        det = self.profile.get("detected_os","")
        if det:
            dl = QLabel(f"Auto-detected as: {det}"); dl.setStyleSheet("color:#2471A3; font-style:italic;"); gl.addRow("", dl)
        gen_w.setLayout(gl); self.tabs.addTab(gen_w, "General")

        # System
        cpu_w = QWidget(); cl = QVBoxLayout(); cm = self.profile.get("cpu_mem",{})
        ag = QGroupBox("Architecture"); al = QVBoxLayout()
        self.arch_combo = QComboBox()
        self.arch_combo.addItems(["x86_64","i386","arm","aarch64","mips","mips64","ppc","ppc64","riscv32","riscv64","sparc","sparc64"])
        self.arch_combo.setCurrentText(cm.get("architecture","x86_64")); al.addWidget(self.arch_combo)
        self.arch_warn = QLabel(""); self.arch_warn.setObjectName("warningBanner"); self.arch_warn.setVisible(False); self.arch_warn.setWordWrap(True)
        al.addWidget(self.arch_warn); ag.setLayout(al); cl.addWidget(ag)
        pg = QGroupBox("Processor"); pfl = QFormLayout()
        self.cpu_model = QLineEdit(cm.get("cpu_model","host")); pfl.addRow("CPU Model:", self.cpu_model)
        self.cpu_cores = QSpinBox(); self.cpu_cores.setRange(1,256); self.cpu_cores.setValue(cm.get("cores",2)); pfl.addRow("Cores:", self.cpu_cores)
        self.cpu_threads = QSpinBox(); self.cpu_threads.setRange(1,256); self.cpu_threads.setValue(cm.get("threads",1)); pfl.addRow("Threads:", self.cpu_threads)
        self.cpu_sockets = QSpinBox(); self.cpu_sockets.setRange(1,256); self.cpu_sockets.setValue(cm.get("sockets",1)); pfl.addRow("Sockets:", self.cpu_sockets)
        pg.setLayout(pfl); cl.addWidget(pg)
        mg = QGroupBox("Memory"); mfl = QFormLayout()
        self.memory = QSpinBox(); self.memory.setRange(64,524288); self.memory.setSingleStep(512)
        self.memory.setValue(cm.get("memory",2048)); self.memory.setSuffix(" MB"); mfl.addRow("Base Memory:", self.memory)
        mg.setLayout(mfl); cl.addWidget(mg); cl.addStretch(); cpu_w.setLayout(cl); self.tabs.addTab(cpu_w, "System")

        # Storage
        sto_w = QWidget(); slo = QVBoxLayout(); st = self.profile.get("storage",{})
        dg = QGroupBox("Hard Disks"); dfl = QVBoxLayout()
        for lt, attr in [("Primary Disk:","hda_path"),("Secondary Disk:","hdb_path")]:
            row = QHBoxLayout(); row.addWidget(QLabel(lt))
            le = QLineEdit(st.get(attr.replace("_path",""),"")); setattr(self, attr, le); row.addWidget(le)
            bb = QPushButton("Browse..."); bb.clicked.connect(lambda c=False,l=le: self._browse_disk_for(l)); row.addWidget(bb); dfl.addLayout(row)
        cb = QPushButton("Create New Disk Image..."); cb.clicked.connect(self._create_disk); dfl.addWidget(cb)
        dg.setLayout(dfl); slo.addWidget(dg)
        cg = QGroupBox("Optical Drive"); cdl = QHBoxLayout(); cdl.addWidget(QLabel("ISO Image:"))
        self.cdrom_path = QLineEdit(st.get("cdrom","")); cdl.addWidget(self.cdrom_path)
        cdb = QPushButton("Browse..."); cdb.clicked.connect(lambda: self._browse_iso_for(self.cdrom_path)); cdl.addWidget(cdb)
        cg.setLayout(cdl); slo.addWidget(cg)
        bg = QGroupBox("Boot Order"); bfl = QFormLayout()
        self.boot_order = QComboBox(); self.boot_order.addItems(["Hard Disk (c)","CD-ROM (d)","Network (n)","Custom"])
        self.boot_order.setCurrentText(st.get("boot","Hard Disk (c)")); bfl.addRow("Boot from:", self.boot_order)
        bg.setLayout(bfl); slo.addWidget(bg); slo.addStretch(); sto_w.setLayout(slo); self.tabs.addTab(sto_w, "Storage")

        # Display
        da_w = QWidget(); dal = QVBoxLayout(); ds = self.profile.get("display_sound",{})
        dpg = QGroupBox("Display"); dfl2 = QFormLayout()
        self.graphics = QComboBox(); dfl2.addRow("Graphics Card:", self.graphics)
        self.display_type = QComboBox(); self.display_type.addItems(["gtk","sdl","vnc","none","spice"])
        self.display_type.setCurrentText(ds.get("display","gtk")); dfl2.addRow("Display Backend:", self.display_type)
        self.fullscreen = QCheckBox("Start in fullscreen"); self.fullscreen.setChecked(ds.get("fullscreen",False)); dfl2.addRow("", self.fullscreen)
        self.display_warn = QLabel(""); self.display_warn.setObjectName("warningBanner"); self.display_warn.setVisible(False); self.display_warn.setWordWrap(True)
        dfl2.addRow("", self.display_warn); dpg.setLayout(dfl2); dal.addWidget(dpg)
        sng = QGroupBox("Audio"); sfl = QFormLayout()
        self.sound_card = QComboBox(); self.sound_card.addItems(["none","ac97","es1370","sb16","hda","intel-hda"])
        self.sound_card.setCurrentText(ds.get("sound_card","none")); sfl.addRow("Sound Card:", self.sound_card)
        self.audio_driver = QComboBox(); self.audio_driver.addItems(["none","dsound","sdl","spice"])
        self.audio_driver.setCurrentText(ds.get("audio_driver","dsound")); sfl.addRow("Audio Driver:", self.audio_driver)
        self.audio_warn = QLabel(""); self.audio_warn.setObjectName("warningBanner"); self.audio_warn.setVisible(False); self.audio_warn.setWordWrap(True)
        sfl.addRow("", self.audio_warn); sng.setLayout(sfl); dal.addWidget(sng)
        dal.addStretch(); da_w.setLayout(dal); self.tabs.addTab(da_w, "Display")

        # Network
        net_w = QWidget(); nl = QVBoxLayout(); nt = self.profile.get("network",{})
        ng = QGroupBox("Network"); nfl = QFormLayout()
        self.net_mode = QComboBox(); self.net_mode.addItems(["User Mode (NAT)","TAP/Bridge","None"])
        self.net_mode.setCurrentText(nt.get("mode","User Mode (NAT)")); nfl.addRow("Attached to:", self.net_mode)
        self.nic_model = QComboBox(); nfl.addRow("Adapter Type:", self.nic_model)
        ng.setLayout(nfl); nl.addWidget(ng); nl.addStretch(); net_w.setLayout(nl); self.tabs.addTab(net_w, "Network")

        # Acceleration
        misc_w = QWidget(); ml2 = QVBoxLayout(); mi = self.profile.get("misc",{})
        avail = get_available_accels()
        acg = QGroupBox("Acceleration"); avl = QVBoxLayout()
        self.enable_kvm = QCheckBox("Enable KVM (Linux)"); self.enable_kvm.setChecked(mi.get("kvm",False))
        if "kvm" not in avail: self.enable_kvm.setEnabled(False); self.enable_kvm.setChecked(False); self.enable_kvm.setToolTip("KVM is only available on Linux hosts")
        avl.addWidget(self.enable_kvm)
        self.enable_whpx = QCheckBox("Enable WHPX (Windows Hypervisor Platform)"); self.enable_whpx.setChecked(mi.get("whpx",False))
        if "whpx" not in avail: self.enable_whpx.setEnabled(False); self.enable_whpx.setChecked(False); self.enable_whpx.setToolTip("WHPX is only available on Windows hosts")
        avl.addWidget(self.enable_whpx)
        self.enable_hax = QCheckBox("Enable HAX (Intel HAXM)"); self.enable_hax.setChecked(mi.get("hax",False))
        if "hax" not in avail: self.enable_hax.setEnabled(False); self.enable_hax.setChecked(False); self.enable_hax.setToolTip("HAX is not available on this platform")
        avl.addWidget(self.enable_hax)
        self.accel_warn = QLabel(""); self.accel_warn.setObjectName("warningBanner"); self.accel_warn.setVisible(False); self.accel_warn.setWordWrap(True)
        avl.addWidget(self.accel_warn); acg.setLayout(avl); ml2.addWidget(acg)
        ug = QGroupBox("USB"); ufl = QFormLayout()
        self.enable_usb = QCheckBox("Enable USB Controller"); self.enable_usb.setChecked(mi.get("usb_enabled",True)); ufl.addRow(self.enable_usb)
        self.usb_type = QComboBox(); self.usb_type.addItems(["usb-ehci","usb-xhci","usb-uhci"])
        self.usb_type.setCurrentText(mi.get("usb_type","usb-ehci")); ufl.addRow("USB Version:", self.usb_type)
        ug.setLayout(ufl); ml2.addWidget(ug)
        big = QGroupBox("BIOS / Firmware"); bfl2 = QFormLayout()
        self.bios_type = QComboBox(); self.bios_type.addItems(["Default (SeaBIOS)","UEFI (OVMF)","Custom"])
        self.bios_type.setCurrentText(mi.get("bios","Default (SeaBIOS)")); bfl2.addRow("BIOS Type:", self.bios_type)
        self.bios_warn = QLabel(""); self.bios_warn.setObjectName("warningBanner"); self.bios_warn.setVisible(False); self.bios_warn.setWordWrap(True)
        bfl2.addRow("", self.bios_warn); big.setLayout(bfl2); ml2.addWidget(big)
        eg = QGroupBox("Additional Arguments"); efl = QFormLayout()
        self.extra_args = QLineEdit(mi.get("extra_args","")); efl.addRow("Custom args:", self.extra_args)
        eg.setLayout(efl); ml2.addWidget(eg); ml2.addStretch(); misc_w.setLayout(ml2); self.tabs.addTab(misc_w, "Acceleration")

        layout.addWidget(self.tabs)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._accept); bbox.rejected.connect(self.reject); layout.addWidget(bbox)
        self.setLayout(layout)

        # Wire compatibility signals
        self.arch_combo.currentTextChanged.connect(self._on_arch_changed)
        self.graphics.currentTextChanged.connect(self._check_display_compat)
        self.display_type.currentTextChanged.connect(self._check_display_compat)
        self.sound_card.currentTextChanged.connect(self._check_audio_compat)
        self.audio_driver.currentTextChanged.connect(self._check_audio_compat)
        self.bios_type.currentTextChanged.connect(self._check_bios_compat)
        self.enable_kvm.stateChanged.connect(self._check_accel_compat)
        self.enable_whpx.stateChanged.connect(self._check_accel_compat)
        self.enable_hax.stateChanged.connect(self._check_accel_compat)
        self.enable_usb.stateChanged.connect(lambda s: self.usb_type.setEnabled(bool(s)))
        self.cpu_model.textChanged.connect(lambda: self._check_accel_compat())
        # Initial population
        self._on_arch_changed(self.arch_combo.currentText())
        self._check_audio_compat(); self._check_bios_compat()

    def _on_arch_changed(self, arch):
        self._updating = True
        old_gfx = self.profile.get("display_sound",{}).get("graphics", self.graphics.currentText())
        valid_gfx = get_valid_graphics(arch); self.graphics.clear(); self.graphics.addItems(valid_gfx)
        self.graphics.setCurrentText(old_gfx if old_gfx in valid_gfx else valid_gfx[0])
        old_nic = self.profile.get("network",{}).get("nic", self.nic_model.currentText())
        valid_nics = get_valid_nics(arch); self.nic_model.clear(); self.nic_model.addItems(valid_nics)
        self.nic_model.setCurrentText(old_nic if old_nic in valid_nics else valid_nics[0])
        if arch in ("ppc","ppc64"):
            self.arch_warn.setText("PowerPC: 'host' CPU only works with KVM. Try 'G4' or 'POWER8' instead."); self.arch_warn.setVisible(True)
        elif arch in ("arm","aarch64"):
            self.arch_warn.setText("ARM: 'host' CPU only works with KVM. Try 'cortex-a53' or 'max' instead."); self.arch_warn.setVisible(True)
        else: self.arch_warn.setVisible(False)
        self._updating = False; self._check_bios_compat(); self._check_display_compat()

    def _check_display_compat(self):
        if self._updating: return
        gfx = self.graphics.currentText(); disp = self.display_type.currentText(); w = []
        if gfx == "qxl" and disp not in ("spice","gtk"): w.append("QXL graphics works best with Spice or GTK display.")
        if disp == "spice" and gfx not in ("qxl","virtio","std"): w.append("Spice display works best with QXL or VirtIO graphics.")
        if gfx == "vmware" and disp == "spice": w.append("VMware graphics is not compatible with Spice display.")
        self.display_warn.setText("\n".join(w)); self.display_warn.setVisible(bool(w))

    def _check_audio_compat(self):
        card = self.sound_card.currentText(); drv = self.audio_driver.currentText(); w = []
        if card != "none" and drv == "none": w.append("Sound card selected but audio driver is 'none'. No audio output.")
        if card == "none" and drv != "none": w.append("Audio driver set but no sound card selected.")
        if drv == "spice" and self.display_type.currentText() != "spice": w.append("Spice audio driver requires Spice display backend.")
        self.audio_warn.setText("\n".join(w)); self.audio_warn.setVisible(bool(w))

    def _check_bios_compat(self):
        if self.bios_type.currentText() == "UEFI (OVMF)" and not can_use_uefi(self.arch_combo.currentText()):
            self.bios_warn.setText(f"UEFI not supported on {self.arch_combo.currentText()}. Only x86_64, i386, aarch64 support OVMF.")
            self.bios_warn.setVisible(True); self.bios_type.setCurrentText("Default (SeaBIOS)")
        else: self.bios_warn.setVisible(False)

    def _check_accel_compat(self):
        c = []
        if self.enable_kvm.isChecked(): c.append("KVM")
        if self.enable_whpx.isChecked(): c.append("WHPX")
        if self.enable_hax.isChecked(): c.append("HAX")
        w = []
        if len(c) > 1:
            w.append(f"Multiple accelerators ({', '.join(c)}). Usually only one should be enabled.")
        if self.enable_whpx.isChecked() and self.cpu_model.text().strip().lower() == "host":
            w.append("WHPX with '-cpu host' can be unstable. 'kernel-irqchip=off' will be added automatically. If the VM still crashes, try changing CPU model to 'qemu64'.")
        if not c and self.cpu_model.text().strip().lower() == "host":
            w.append("No accelerator enabled — '-cpu host' requires one. The launcher will use 'qemu64' automatically.")
        self.accel_warn.setText("\n".join(w)); self.accel_warn.setVisible(bool(w))

    def _browse_disk_for(self, le):
        f, _ = QFileDialog.getOpenFileName(self,"Select Disk Image","","Disk Images (*.qcow2 *.img *.vdi *.vmdk *.raw);;All (*.*)")
        if f: le.setText(f)
    def _browse_iso_for(self, le):
        f, _ = QFileDialog.getOpenFileName(self,"Select ISO","","ISO Images (*.iso);;All (*.*)")
        if f: le.setText(f)
    def _create_disk(self):
        dlg = CreateDiskDialog(self)
        if dlg.exec() == QDialog.Accepted:
            reply = QMessageBox.question(self,"Add Disk?","Use as Primary or Secondary?\n\nYes = Primary\nNo = Secondary", QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
            if reply == QMessageBox.Yes: self.hda_path.setText(dlg.file_path.text())
            elif reply == QMessageBox.No: self.hdb_path.setText(dlg.file_path.text())
    def _accept(self):
        arch = self.arch_combo.currentText()
        if self.bios_type.currentText() == "UEFI (OVMF)" and not can_use_uefi(arch):
            QMessageBox.warning(self,"Incompatible",f"UEFI not available for {arch}. Change BIOS or architecture."); return
        self.profile["name"] = self.name_edit.text().strip() or "VM"
        self.profile["os_type"] = self.os_combo.currentText()
        self.profile["cpu_mem"] = {"architecture": arch, "cpu_model": self.cpu_model.text(), "cores": self.cpu_cores.value(), "threads": self.cpu_threads.value(), "sockets": self.cpu_sockets.value(), "memory": self.memory.value()}
        self.profile["storage"] = {"hda": self.hda_path.text(), "hdb": self.hdb_path.text(), "cdrom": self.cdrom_path.text(), "boot": self.boot_order.currentText()}
        self.profile["display_sound"] = {"graphics": self.graphics.currentText(), "display": self.display_type.currentText(), "fullscreen": self.fullscreen.isChecked(), "sound_card": self.sound_card.currentText(), "audio_driver": self.audio_driver.currentText()}
        self.profile["network"] = {"mode": self.net_mode.currentText(), "nic": self.nic_model.currentText()}
        self.profile["misc"] = {"kvm": self.enable_kvm.isChecked(), "whpx": self.enable_whpx.isChecked(), "hax": self.enable_hax.isChecked(), "usb_enabled": self.enable_usb.isChecked(), "usb_type": self.usb_type.currentText(), "bios": self.bios_type.currentText(), "extra_args": self.extra_args.text()}
        self.accept()

# === DETAIL PANEL ===
class DetailPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("detailPanel"); self.setFrameShape(QFrame.StyledPanel)
        self._layout = QVBoxLayout(); self._layout.setContentsMargins(16,16,16,16)
        header = QHBoxLayout()
        self.icon_label = QLabel(); self.icon_label.setFixedSize(48,48); header.addWidget(self.icon_label)
        self.title_label = QLabel("No VM Selected"); self.title_label.setFont(QFont("Segoe UI",16,QFont.Bold))
        self.title_label.setStyleSheet("color: #2C3E50;"); header.addWidget(self.title_label); header.addStretch()
        self._layout.addLayout(header)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setStyleSheet("color:#D0D8E0;"); self._layout.addWidget(sep)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        self.info_widget = QWidget(); self.info_layout = QVBoxLayout(); self.info_layout.setSpacing(2)
        self.info_widget.setLayout(self.info_layout); scroll.setWidget(self.info_widget); self._layout.addWidget(scroll, 1)
        self.cmd_group = QGroupBox("QEMU Command"); cmd_layout = QVBoxLayout()
        self.command_preview = QTextEdit(); self.command_preview.setReadOnly(True); self.command_preview.setMaximumHeight(100)
        cmd_layout.addWidget(self.command_preview); self.cmd_group.setLayout(cmd_layout)
        self._layout.addWidget(self.cmd_group); self.cmd_group.setVisible(False); self.setLayout(self._layout)
    def clear(self):
        self.title_label.setText("No VM Selected"); self.icon_label.clear()
        self.command_preview.clear(); self.cmd_group.setVisible(False)
        while self.info_layout.count():
            w = self.info_layout.takeAt(0).widget()
            if w: w.deleteLater()
    def show_profile(self, profile):
        self.clear()
        if not profile: return
        name = profile.get("name","VM"); os_type = profile.get("os_type","Other")
        self.title_label.setText(name); self.icon_label.setPixmap(make_os_icon(os_type,48).pixmap(48,48))
        cm = profile.get("cpu_mem",{}); st = profile.get("storage",{}); ds = profile.get("display_sound",{})
        nt = profile.get("network",{}); mi = profile.get("misc",{}); det = profile.get("detected_os","")
        sections = [
            ("General", [("Operating System", os_type)] + ([("Detected OS", det)] if det else [])),
            ("System", [("Architecture",cm.get("architecture","—")),("CPU Model",cm.get("cpu_model","—")),
                ("Processors",f"{cm.get('cores',1)} core(s), {cm.get('threads',1)} thread(s), {cm.get('sockets',1)} socket(s)"),
                ("Base Memory",f"{cm.get('memory',0)} MB")]),
            ("Storage", [("Primary Disk",st.get("hda") or "Not attached"),("Secondary Disk",st.get("hdb") or "Not attached"),
                ("Optical Drive",st.get("cdrom") or "Empty"),("Boot Order",st.get("boot","—"))]),
            ("Display", [("Graphics",ds.get("graphics","—")),("Display Backend",ds.get("display","—")),
                ("Fullscreen","Yes" if ds.get("fullscreen") else "No"),("Sound Card",ds.get("sound_card","none")),
                ("Audio Driver",ds.get("audio_driver","none"))]),
            ("Network", [("Attached to",nt.get("mode","—")),("Adapter Type",nt.get("nic","—"))]),
            ("Acceleration", [("KVM","Enabled" if mi.get("kvm") else "Disabled"),("WHPX","Enabled" if mi.get("whpx") else "Disabled"),
                ("HAX","Enabled" if mi.get("hax") else "Disabled"),
                ("USB",mi.get("usb_type","—") if mi.get("usb_enabled") else "Disabled"),("BIOS",mi.get("bios","—"))]),
        ]
        for st_title, rows in sections:
            h = QLabel(f"  {st_title}"); h.setFont(QFont("Segoe UI",11,QFont.Bold)); h.setStyleSheet("color:#34495E; margin-top:8px;")
            self.info_layout.addWidget(h)
            for key, val in rows:
                rw = QWidget(); rl = QHBoxLayout(); rl.setContentsMargins(20,1,8,1)
                kl = QLabel(key+":"); kl.setFixedWidth(140); kl.setStyleSheet("color:#7F8C8D; font-size:12px;"); kl.setAlignment(Qt.AlignRight|Qt.AlignVCenter); rl.addWidget(kl)
                vl = QLabel(str(val)); vl.setStyleSheet("color:#2C3E50; font-size:12px;"); vl.setWordWrap(True); rl.addWidget(vl, 1)
                rw.setLayout(rl); self.info_layout.addWidget(rw)
        self.info_layout.addStretch()
        cmd = build_qemu_command(profile)
        self.command_preview.setPlainText(" ".join(f'"{a}"' if " " in a else a for a in cmd)); self.cmd_group.setVisible(True)

# === QEMU COMMAND BUILDER ===
def build_qemu_command(profile):
    cm = profile.get("cpu_mem",{}); st = profile.get("storage",{}); ds = profile.get("display_sound",{})
    nt = profile.get("network",{}); mi = profile.get("misc",{})
    arch = cm.get("architecture","x86_64"); exe = os.path.join(QEMU_PATH, f"qemu-system-{arch}.exe")
    cpu_model = cm.get("cpu_model","host")
    has_accel = mi.get("kvm") or mi.get("whpx") or mi.get("hax")
    # -cpu host only works with a hypervisor; TCG needs a named model
    if cpu_model.lower() == "host" and not has_accel:
        cpu_model = "qemu64"
    args = [exe, "-cpu", cpu_model]
    smp = str(cm.get("cores",2))
    if cm.get("threads",1) > 1: smp += f",threads={cm['threads']}"
    if cm.get("sockets",1) > 1: smp += f",sockets={cm['sockets']}"
    args += ["-smp", smp, "-m", str(cm.get("memory",2048))]
    if st.get("hda"): args += ["-hda", st["hda"]]
    if st.get("hdb"): args += ["-hdb", st["hdb"]]
    if st.get("cdrom"): args += ["-cdrom", st["cdrom"]]
    bm = {"Hard Disk (c)":"c","CD-ROM (d)":"d","Network (n)":"n"}
    b = bm.get(st.get("boot"))
    if b: args += ["-boot", b]
    args += ["-vga", ds.get("graphics","std")]
    dt = ds.get("display","gtk")
    if dt == "vnc": args += ["-display","vnc=:0"]
    elif dt != "none": args += ["-display", dt]
    if ds.get("fullscreen"): args.append("-full-screen")
    snd_card = ds.get("sound_card","none"); snd_drv = ds.get("audio_driver","none")
    if snd_drv != "none" and snd_card != "none":
        args += ["-audiodev", f"{snd_drv},id=snd0"]
        if snd_card in ("intel-hda", "hda"):
            args += ["-device", "intel-hda", "-device", "hda-duplex,audiodev=snd0"]
        else:
            args += ["-device", f"{snd_card},audiodev=snd0"]
    elif snd_card != "none":
        args += ["-audio", "none", "-device", snd_card]
    if nt.get("mode") == "User Mode (NAT)": args += ["-netdev","user,id=net0","-device",f"{nt.get('nic','e1000')},netdev=net0"]
    elif nt.get("mode") == "None": args += ["-nic","none"]
    if mi.get("kvm"): args += ["-accel", "kvm"]
    if mi.get("whpx"): args += ["-accel", "whpx,kernel-irqchip=off"]
    if mi.get("hax"): args += ["-accel", "hax"]
    if mi.get("usb_enabled"): args += ["-device", mi.get("usb_type","usb-ehci")]
    if mi.get("bios") == "UEFI (OVMF)": args += ["-bios","OVMF.fd"]
    extra = mi.get("extra_args","").strip()
    if extra: args += extra.split()
    return args

# === MAIN WINDOW ===
class QEMUMainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("QEMU Virtual Machine Manager"); self.setGeometry(80,80,1050,680)
        self._vm_map = {}
        tb = QToolBar("Main Toolbar"); tb.setMovable(False); tb.setIconSize(QSize(28,28))
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon); self.addToolBar(tb)
        self.act_new = QAction(make_toolbar_icon("new","#2980B9"),"New",self); self.act_new.triggered.connect(self.new_vm); tb.addAction(self.act_new)
        self.act_settings = QAction(make_toolbar_icon("settings","#8E44AD"),"Settings",self); self.act_settings.triggered.connect(self.open_settings); self.act_settings.setEnabled(False); tb.addAction(self.act_settings); tb.addSeparator()
        self.act_start = QAction(make_toolbar_icon("start","#27AE60"),"Start",self); self.act_start.triggered.connect(self.start_vm); self.act_start.setEnabled(False); tb.addAction(self.act_start); tb.addSeparator()
        self.act_clone = QAction(make_toolbar_icon("clone","#4A6484"),"Clone",self); self.act_clone.triggered.connect(self.clone_vm); self.act_clone.setEnabled(False); tb.addAction(self.act_clone)
        self.act_remove = QAction(make_toolbar_icon("remove","#C0392B"),"Remove",self); self.act_remove.triggered.connect(self.remove_vm); self.act_remove.setEnabled(False); tb.addAction(self.act_remove); tb.addSeparator()
        self.act_import = QAction(make_toolbar_icon("import","#16A085"),"Import",self); self.act_import.triggered.connect(self.import_profile); tb.addAction(self.act_import)
        self.act_export = QAction(make_toolbar_icon("export","#2C3E50"),"Export",self); self.act_export.triggered.connect(self.export_profile); self.act_export.setEnabled(False); tb.addAction(self.act_export)
        sp = QSplitter(Qt.Horizontal)
        self.vm_list = QListWidget(); self.vm_list.setObjectName("vmList"); self.vm_list.setIconSize(QSize(32,32))
        self.vm_list.setMinimumWidth(220); self.vm_list.setMaximumWidth(350); self.vm_list.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.vm_list.currentItemChanged.connect(self._on_sel); self.vm_list.doubleClicked.connect(self.open_settings)
        self.vm_list.setContextMenuPolicy(Qt.CustomContextMenu); self.vm_list.customContextMenuRequested.connect(self._ctx)
        sp.addWidget(self.vm_list); self.detail_panel = DetailPanel(); sp.addWidget(self.detail_panel)
        sp.setSizes([260,780]); self.setCentralWidget(sp)
        self.statusBar().showMessage(f"Profiles: {PROFILES_DIR}  |  Host: {HOST_OS}")
        self.refresh_list()
    def refresh_list(self):
        cur = self._sel_uid(); self.vm_list.clear(); self._vm_map.clear()
        for uid, p in ProfileManager.list_profiles():
            self._vm_map[uid] = p; name = p.get("name","VM"); ot = p.get("os_type","Other"); mem = p.get("cpu_mem",{}).get("memory",0)
            it = QListWidgetItem(make_os_icon(ot,32), f"{name}\n{ot}  \u2022  {mem} MB"); it.setData(Qt.UserRole, uid); it.setSizeHint(QSize(0,52))
            self.vm_list.addItem(it)
        if cur:
            for i in range(self.vm_list.count()):
                if self.vm_list.item(i).data(Qt.UserRole) == cur: self.vm_list.setCurrentRow(i); return
        if self.vm_list.count(): self.vm_list.setCurrentRow(0)
    def _sel_uid(self):
        it = self.vm_list.currentItem(); return it.data(Qt.UserRole) if it else None
    def _sel_profile(self):
        uid = self._sel_uid(); return self._vm_map.get(uid) if uid else None
    def _on_sel(self, cur, prev):
        has = cur is not None
        for a in (self.act_settings,self.act_start,self.act_clone,self.act_remove,self.act_export): a.setEnabled(has)
        if has: self.detail_panel.show_profile(self._vm_map.get(cur.data(Qt.UserRole)))
        else: self.detail_panel.clear()
    def _ctx(self, pos):
        if not self.vm_list.itemAt(pos): return
        m = QMenu(self); m.addAction("Settings...",self.open_settings); m.addAction("Start",self.start_vm)
        m.addSeparator(); m.addAction("Clone",self.clone_vm); m.addAction("Rename...",self.rename_vm)
        m.addSeparator(); m.addAction("Export...",self.export_profile); m.addSeparator(); m.addAction("Remove",self.remove_vm)
        m.exec(self.vm_list.viewport().mapToGlobal(pos))
    def new_vm(self):
        dlg = NewVMDialog(self)
        if dlg.exec() == QDialog.Accepted:
            uid = ProfileManager.new_uid(); p = dlg.get_profile(); ProfileManager.save(uid, p); self.refresh_list()
            for i in range(self.vm_list.count()):
                if self.vm_list.item(i).data(Qt.UserRole) == uid: self.vm_list.setCurrentRow(i); break
            self.statusBar().showMessage(f"Created VM: {p['name']}", 4000)
    def open_settings(self):
        uid = self._sel_uid(); p = self._sel_profile()
        if not uid or not p: return
        dlg = SettingsDialog(p, self)
        if dlg.exec() == QDialog.Accepted:
            ProfileManager.save(uid, dlg.profile); self._vm_map[uid] = dlg.profile
            self.refresh_list(); self.statusBar().showMessage("Settings saved.", 3000)
    def start_vm(self):
        p = self._sel_profile()
        if not p: return
        cmd = build_qemu_command(p)
        if not os.path.exists(cmd[0]):
            QMessageBox.critical(self,"Error",f"QEMU not found:\n{cmd[0]}\n\nInstall QEMU at {QEMU_PATH}"); return
        try:
            subprocess.Popen(cmd, creationflags=getattr(subprocess,"CREATE_NEW_CONSOLE",0))
            self.statusBar().showMessage(f"Started VM: {p['name']}", 4000)
        except Exception as e: QMessageBox.critical(self,"Error",f"Failed to start:\n{e}")
    def clone_vm(self):
        p = self._sel_profile()
        if not p: return
        nid = ProfileManager.new_uid(); c = json.loads(json.dumps(p)); c["name"] += " (Clone)"
        ProfileManager.save(nid, c); self.refresh_list(); self.statusBar().showMessage(f"Cloned: {c['name']}", 4000)
    def rename_vm(self):
        uid = self._sel_uid(); p = self._sel_profile()
        if not p: return
        name, ok = QInputDialog.getText(self,"Rename VM","New name:",text=p.get("name",""))
        if ok and name.strip():
            p["name"] = name.strip(); ProfileManager.save(uid, p); self._vm_map[uid] = p; self.refresh_list()
    def remove_vm(self):
        uid = self._sel_uid(); p = self._sel_profile()
        if not p: return
        if QMessageBox.question(self,"Remove VM",f"Remove \"{p.get('name','VM')}\"?\n\nDisk images are not affected.",QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            ProfileManager.delete(uid); self.refresh_list(); self.statusBar().showMessage("VM removed.", 3000)
    def import_profile(self):
        f, _ = QFileDialog.getOpenFileName(self,"Import Profile","","JSON (*.json)")
        if not f: return
        try:
            data = json.loads(Path(f).read_text()); uid = ProfileManager.new_uid()
            for k in DEFAULT_PROFILE:
                if k not in data: data[k] = DEFAULT_PROFILE[k]
            ProfileManager.save(uid, data); self.refresh_list()
            self.statusBar().showMessage(f"Imported: {data.get('name','VM')}", 4000)
        except Exception as e: QMessageBox.critical(self,"Import Error",str(e))
    def export_profile(self):
        p = self._sel_profile()
        if not p: return
        d = p.get("name","vm").replace(" ","_") + ".json"
        f, _ = QFileDialog.getSaveFileName(self,"Export Profile",d,"JSON (*.json)")
        if f:
            try: Path(f).write_text(json.dumps(p, indent=4)); self.statusBar().showMessage(f"Exported: {f}", 4000)
            except Exception as e: QMessageBox.critical(self,"Export Error",str(e))

def main():
    app = QApplication(sys.argv); app.setStyle("Fusion"); app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Segoe UI", 10)); w = QEMUMainWindow(); w.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()
