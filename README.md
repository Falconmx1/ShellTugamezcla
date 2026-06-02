# 🐢 ShellTuga - The Turtle-Powered Forensic Browser

![ShellTuga Banner](assets/tortuga_banner.png)

> *"Slow but deep analysis. Like a turtle, but with claws."*

**ShellTuga** is a desktop GUI that wraps **The Sleuth Kit (TSK)** command-line tools into an easy-to-use forensic browser. No more typing `fls`, `icat`, `ils` manually. Click, analyze, conquer.

---

## ✨ Features

- 🖥️ **Graphical interface** for TSK (Autopsy-style but lighter)
- 📂 Supports **NTFS, FAT, EXT2/3/4, FFS**
- 🔍 File browser with deleted file highlighting
- 📜 Hex viewer and metadata inspector
- 🐢 **Turtle Mascot** – because real forensics take time and patience
- 💾 Disk image support (raw, E01 via libewf optional)

---

## 🧰 Requirements

- Python 3.8+
- The Sleuth Kit (`tsk` installed in PATH)
- Tkinter or PyQt5

---

## 📦 Installation

```bash
git clone https://github.com/Falconmx1/ShellTuga-Forensic.git
cd ShellTuga-Forensic
pip install -r requirements.txt
python shelltuga.py
