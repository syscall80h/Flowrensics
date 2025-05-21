# Flowrensics: Automate Windows Forensics Artifacts

![License](https://img.shields.io/github/license/syscall80h/Flowrensics)
![Python](https://img.shields.io/badge/python-3.10%2B-80ffd8)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-99a5ff)
![Status](https://img.shields.io/badge/version-1.0.0-d1c2ff)

> **Flowrensics** automates the collection and analysis of key Windows forensic artifacts.  
> It orchestrates **Eric Zimmerman’s EZ Tools**, **Hayabusa**, and **Volatility 3**.

---

## Table of Contents
1. [Features](#features)  
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)  
4. [Usage](#usage)  
5. [Results](#results)  
6. [Roadmap](#roadmap)   
7. [License](#license) 

---

## Features
- **One-click triage** of Windows artifacts via EZ Tools (MFT, Prefetch, Registry hives, Event Logs, etc.).  
- **Memory analysis** pipeline powered by Volatility 3.  
- **Fast threat-hunting timeline** generation with Hayabusa (Sigma-rule-aware).  
- **Auto-download & update**: Hayabusa and Volatility binaries are fetched on first use.  
- **Parallel execution** with live progress and colorised logs.  
- **Self-contained**: all scripts run inside a Python virtual environment; no system-wide installs required.  
- **Results folder** structured for quick ingestion in Splunk, Timesketch, or Excel.  
- **Tested on Windows 10 & 11**.  

---

## Prerequies
> [!IMPORTANT]
> **Requirements to run Flowrensics:**
> OS: Windows 10 or Windows 11
> Analysis Tools: Eric Zimmerman’s EZ Tools with the .NET 6 or .NET 9 desktop runtime installed
> Python: 3.10 or newer (64-bit)

> [!NOTE]
> Hayabusa and Volatility are downloaded automatically the first time each module is invoked.

> [!WARNING]
> Volatility and Hayabusa can be resource- and time-intensive—plan accordingly.

---

## Quick Start
```powershell
# Clone and enter the repo
> git clone https://github.com/syscall80h/Flowrensics.git
> cd Flowrensics

# Set up an isolated environment (PowerShell)
> py -m venv venv
> .\venv\Scripts\Activate.ps1

# Install Python dependencies
(venv) > pip install -r requirements.txt

# Launch the GUI
(venv) > py main.py
```
---
## Usage
![image](https://github.com/user-attachments/assets/93ef8839-7d9c-4ebc-ab8a-20db2d094bf7)

1. EZ Tools directory – browse to the ```net``` sub-folder containing the command-line EXEs.
![image](https://github.com/user-attachments/assets/1796a2b5-3d7d-4aef-b041-401ee632c97f)

2. Triage directory – select the root of the collection (e.g. the drive-letter folder).
![image](https://github.com/user-attachments/assets/317426a6-86fa-45ad-999e-2b4c5a9b875a)


> [!IMPORTANT]
> Selecting the triage directory enables the Run Selected Tools button.

### Sections
- Windows Artifacts – choose individual EZ modules or run the full sweep.
- Memory Analysis – point to a raw memory dump and pick Volatility plugins.

---

## Results
All output is written to the Output directory, organised per module:
```
Output\
 ├─ EZ output     # CSV from EZ Tools
 ├─ Hayabusa\     # EVTX timeline & Sigma hits
 └─ Volatility\   # Plugin outputs
```
---

## Roadmap
- [ ] Add YARA scan support for memory dumps  
- [ ] Export consolidated timeline to Timesketch directly
- [ ] Run Volatility for a specific PID
- [ ] PDF rapport generated

---

## License
Flowrensics is released under the MIT License – see the LICENSE file for details.
