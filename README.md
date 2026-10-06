# CheevosGrabber

> A modern GUI tool for downloading, organizing, and templating RetroAchievements badges.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-1f6aa5)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Release](https://img.shields.io/github/v/release/<your-user>/CheevosGrabber?label=download)

**CheevosGrabber** is a desktop utility built with Python and CustomTkinter that streamlines the workflow of RetroAchievements badge collectors and community template makers. It fetches achievements directly from the RA API, downloads badges in the correct display order, and generates pixel-perfect **Gauntlet** grids for sharing.

---

## Features

- **Smart Download** — Fetches 64×64 badges directly from the RetroAchievements API using only the Game ID.
- **Native Ordering** — Files are saved with zero-padded numeric prefixes (`001_`, `002_`, …) that preserve the site's exact `DisplayOrder`.
- **Direct API Templating** — Previews and generates full Gauntlet grids entirely in memory, without writing individual badge files to disk.
- **Gauntlet Creator** — Stitches any selection of local badges into a single PNG with a transparent background, locked to a 10-column grid.
- **Dynamic Margins** — Adjust icon spacing (0px, 1px, 2px, 4px) in real time inside the preview window to avoid dark borders blending together.
- **Set Type Selector** — Choose between **Official** and **Unofficial** achievement sets.
- **Remember Credentials** — Optionally persist your username, API key, and destination folder between sessions.
- **Live Game Preview** — Displays the game's icon, title, and total achievement count after each search.

---

## Screenshots

**Main window**

<img width="958" height="664" alt="Main window" src="https://github.com/user-attachments/assets/ecf70214-c32d-4b4e-9934-9087b5690a73" />

**Template preview**

<img width="878" height="664" alt="Template preview" src="https://github.com/user-attachments/assets/55b16751-1b77-4e49-b327-92ae8a5e68b9" />

---

## Getting Started

### Option 1 — Download the executable (recommended)

No Python required. Just grab the latest build from the **[Releases page](https://github.com/CarlosNatanael/CheevosGrabber/releases)** and run `CheevosGrabber.exe`.

1. Go to the [Releases](https://github.com/CarlosNatanael/CheevosGrabber/releases) section.
2. Download the latest `CheevosGrabber.exe`.
3. Run it — no installation needed.
4. Jump straight to [Usage](#usage).

> [!NOTE]
> Windows SmartScreen may warn about an unsigned executable. Click **More info → Run anyway**.

#### Prerequisites

- A **RetroAchievements account** with a **Web API Key**
  → Get yours at [retroachievements.org/settings](https://retroachievements.org/settings?tab=applications) (section *Keys*).

## Usage

### 1. Configure credentials

Enter your **RA Username** and **Web API Key** in the sidebar. Tick **Remember credentials** to save them locally in `config.json` (plain text — keep that file private).

### 2. Search a game

Type the **Game ID** (e.g. `1445`) and click **Search**. The app fetches the title, icon, and total achievement count.

> You can find a game's ID in its RetroAchievements URL: `retroachievements.org/game/1445`.

### 3. Choose an action

| Button | What it does |
|--------|--------------|
| **Preview Template** | Loads all badges for the game directly from the API and renders a live Gauntlet grid you can save as PNG. |
| **Create Gauntlet** | Opens a file picker to select **local PNG badges** and stitches them into a single grid image. |
| **Download Badges** | Saves every badge of the game into `badges_<gameId>_<settype>/` with numbered filenames. |

### 4. Export

In the preview windows, choose the desired margin (0–4px) and hit **Save Template**. The PNG keeps a transparent background and opens automatically afterwards.

---

## Output structure

```
badges/
└── badges_1445_official/
    ├── 001_00001.png
    ├── 002_00002.png
    ├── 003_00003.png
    └── ...
```

Filenames follow the pattern `NNN_BadgeName.png`, where `NNN` mirrors the achievement's `DisplayOrder`.

---

## Configuration

The app stores preferences in `config.json` at the project root:

```json
{"save_dir": "C:/path/to/badges", "remember": true, "user": "YourUsername", "api_key": "your_api_key"}
```
> [!IMPORTANT]
> **Security note:** the API key is stored in **plain text**. Only enable *Remember credentials* on a trusted machine, and never commit `config.json` to version control. Add it to `.gitignore`.

---

## Known Limitations

- Supports **PNG** badges only (RA serves badges as PNG, so this is rarely an issue).
- Set Type filter relies on the `f` parameter: `3` = Official, `5` = Unofficial.
- Requires an internet connection for API templating and downloads.
- Auto-open after saving uses `os.startfile` — **Windows only**.

---
