# Qumi
# QEMU Virtual Machine Manager

A VirtualBox-style graphical frontend for QEMU on Windows. Create, configure, and launch QEMU virtual machines without touching the command line.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![PySide6](https://img.shields.io/badge/GUI-PySide6-green) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-orange)

## Features

- **VirtualBox-style interface** — left sidebar VM list, right-side detail panel, toolbar with New / Settings / Start / Clone / Remove / Import / Export
- **Auto-detect OS from ISO** — select an ISO file and the app identifies the operating system from the filename (Windows versions, 20+ Linux distros, macOS codenames back to Tiger, BSDs, Solaris, FreeDOS, and more)
- **Smart presets** — detected OS auto-configures recommended RAM, graphics card, sound card, NIC, BIOS type, USB version, and acceleration based on what that OS needs
- **Incompatibility prevention** — changing architecture auto-filters graphics and NIC options to only show compatible hardware. UEFI auto-reverts on unsupported architectures. Yellow warnings appear for bad combos (QXL without Spice, sound card without audio driver, multiple accelerators, etc.)
- **Platform-aware acceleration** — detects your host OS and grays out unavailable accelerators (KVM on Windows, WHPX on Linux, etc.). WHPX automatically gets `kernel-irqchip=off` to prevent interrupt injection crashes
- **Profile management** — VMs save automatically as JSON files in `~/.qemu-gui/machines/`. Clone, rename, import/export profiles. Old JSON profiles from other tools can be imported directly
- **Command preview** — see the exact QEMU command that will be generated before launching
- **Create disk images** — built-in dialog for creating qcow2, raw, vdi, vmdk, and vhdx disk images via `qemu-img`

## Requirements

- **Windows 10/11** (built for Windows, QEMU path defaults to `C:\Program Files\qemu`)
- **[QEMU for Windows](https://qemu.weilnetz.de/w64/)** — install to the default path `C:\Program Files\qemu`
- **Python 3.8+** (only needed if running from source or building the exe)

## Installation

### Option A: Download the exe (easiest)

1. Go to the [Releases](../../releases) page
2. Download `QEMU-GUI.exe`
3. Double-click to run — no Python needed

### Option B: Run from source

1. Make sure Python 3.8+ is installed
2. Clone the repo:
   ```
   git clone https://github.com/YOUR_USERNAME/qemu-gui.git
   cd qemu-gui
   ```
3. Install PySide6:
   ```
   pip install PySide6
   ```
4. Run:
   ```
   python qemu_gui.py
   ```

### Option C: Build your own exe

1. Clone the repo and `cd` into it
2. Run the build script:
   ```
   python BUILD_EXE.py
   ```
   This will automatically install PyInstaller and PySide6 if needed, then produce a standalone exe at `dist/QEMU-GUI.exe`.
3. Copy `QEMU-GUI.exe` anywhere you want and delete the rest

## Quick Start

1. **Install QEMU** to `C:\Program Files\qemu` if you haven't already
2. **Launch QEMU-GUI**
3. Click **New** in the toolbar
4. Browse for an ISO — the app will auto-detect the OS and fill in recommended settings
5. Adjust the name and RAM if you want, optionally create or attach a disk image
6. Click **OK** to create the VM
7. Select it in the sidebar and click **Start**

## Supported OS Detection

The ISO filename is matched against patterns to identify the OS. Some examples:

| ISO filename | Detected as | Preset highlights |
|---|---|---|
| `Win11_English_x64.iso` | Windows 11 | 4 GB RAM, QXL, HDA sound, UEFI, WHPX |
| `Win7_64_bit.iso` | Windows 7 | 2 GB RAM, std graphics, AC97, SeaBIOS |
| `ubuntu-24.04-desktop-amd64.iso` | Ubuntu 24 | 4 GB RAM, VirtIO graphics + NIC |
| `archlinux-2024.01.01-x86_64.iso` | Arch Linux | 2 GB RAM, VirtIO, intel-hda |
| `alpine-standard-3.19.0-x86_64.iso` | Alpine Linux | 512 MB RAM, lightweight config |
| `Sonoma.iso` | macOS Sonoma | 8 GB RAM, VMware graphics, Penryn CPU, UEFI |
| `Tiger.iso` | macOS Tiger | 512 MB RAM, PowerPC arch, G4 CPU |
| `FreeBSD-14.0-RELEASE-amd64-disc1.iso` | FreeBSD | 1 GB RAM, e1000, SeaBIOS |
| `freedos.iso` | FreeDOS | 64 MB RAM, i386 arch |

Full list includes all Windows versions (XP through 11, Server editions), 20+ Linux distros, macOS codenames (Tiger through Sonoma), BSDs, Solaris, ReactOS, Haiku, TempleOS, KolibriOS, and more.

## Acceleration Notes

| Accelerator | Host OS | Notes |
|---|---|---|
| **WHPX** | Windows | Uses Windows Hypervisor Platform. `kernel-irqchip=off` is added automatically to prevent crashes. Requires Hyper-V or Windows Hypervisor Platform enabled in Windows Features |
| **KVM** | Linux | Best performance. Requires `/dev/kvm` access |
| **HAX** | Windows/macOS | Intel HAXM — must be [installed separately](https://github.com/intel/haxm). Intel CPUs only |
| **TCG** | Any | Software emulation (no checkbox needed). Slower but always works. If CPU model is set to `host` with no accelerator, the launcher automatically uses `qemu64` instead |

If a VM crashes or won't boot, try disabling acceleration in Settings → Acceleration. TCG (software emulation) is slower but the most reliable fallback.

## VM Profiles

Profiles are stored as JSON files in:
```
%USERPROFILE%\.qemu-gui\machines\
```

Each VM is a single `.json` file. You can:
- **Import** profiles from JSON files (including ones hand-written or from other tools)
- **Export** profiles to share with others
- **Clone** VMs to quickly duplicate a config
- **Back up** the whole `machines` folder to save all your VMs

## Files

| File | Description |
|---|---|
| `qemu_gui.py` | Main application |
| `BUILD_EXE.py` | One-click exe builder (installs dependencies automatically) |

## Troubleshooting

**"QEMU executable not found"** — Install QEMU to `C:\Program Files\qemu` or edit the `QEMU_PATH` variable at the top of `qemu_gui.py`.

**VM crashes immediately with WHPX** — The `kernel-irqchip=off` flag is added automatically, but WHPX can still be unstable with certain guest OSes. Try unchecking WHPX in Settings → Acceleration to fall back to TCG.

**VM freezes during boot** — If using WHPX, the CPU model might be incompatible. The app defaults to `host` which usually works with WHPX + `kernel-irqchip=off`, but you can try changing CPU model to `qemu64` in Settings → System → Processor.

**No sound** — Make sure both a sound card AND an audio driver are selected in Settings → Display. The app warns you if they're mismatched.

**White text on white background (dark mode)** — This was fixed in the current version. If you see this on an older version, update to the latest.

## License

MIT

