# CheevosGrabber
A graphical user interface utility developed in Python (CustomTkinter) to manage, download, and organize RetroAchievements achievement badges. It streamlines asset extraction and generates perfectly aligned "Gauntlet" templates for community sharing.

## Features
* **Smart Download:** Fetches 64x64 badges directly from the RetroAchievements API using the game ID.
* **Native Ordering:** Saves files with numerical prefixes (e.g., `001_`, `002_`), preserving the exact `DisplayOrder` from the site.
* **Direct API Templating:** Previews and generates complete Gauntlet grids directly from memory without polluting your local drive with individual icon files.
* **Gauntlet Creator:** Stitches selected local badges into a single PNG image (transparent background) locked to a 10-column grid.
* **Dynamic Margins:** Adjusts icon spacing (0px, 1px, 2px, or 4px) in real-time within the preview window to prevent dark borders from blending together.
