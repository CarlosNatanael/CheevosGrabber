# CheevosGrabber

A graphical user interface utility developed in Python (CustomTkinter) to manage, download, and organize RetroAchievements achievement badges (icons).

## Features

* **Smart Download:** Downloads badges in 64x64 using the game ID directly from the RetroAchievements API.
* **Native Ordering:** Files are saved with numerical prefixes (e.g., `001_`, `002_`), keeping the exact achievement order (DisplayOrder) from the site.
* **Integrated Viewer:** Allows you to preview the game's achievement grid loaded directly into memory before downloading.
* **Gauntlet Creator:** Select local badges and generate a single PNG image (transparent background) with up to 10 columns.
* **Dynamic Margins:** Adjust the spacing between icons in the Gauntlet (0px, 1px, 2px, or 4px) with real-time preview to prevent borders from blending together.
* **Credential Management:** Option to remember your username, API key, and local destination folder.
