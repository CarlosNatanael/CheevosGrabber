import io
import json
import math
import os
import re
import sys
import threading
from tkinter import filedialog

import customtkinter as ctk
import requests
from PIL import Image

# API configuration
API_URL = "https://retroachievements.org/API/API_GetGameExtended.php"
BADGE_URL = "https://media.retroachievements.org/Badge/{}.png"
CONFIG_FILE = "config.json"

# Gauntlet layout
BADGE_SIZE = 64
GRID_COLUMNS = 10
MARGIN_OPTIONS = ["Margin: 0px", "Margin: 1px", "Margin: 2px", "Margin: 4px"]
REQUEST_TIMEOUT = 30


def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def apply_icon(window):
    icon_path = resource_path("icon.ico")
    if not os.path.exists(icon_path):
        return

    def _set_icon():
        try:
            window.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not set window icon: {e}")

    window.after(250, _set_icon)


def fetch_achievements(user, api_key, game_id):
    params = {"z": user, "y": api_key, "i": game_id}
    response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)

    if response.status_code != 200:
        raise ValueError("API Error. Are the credentials correct?")

    data = response.json()
    if "Achievements" not in data or not data["Achievements"]:
        raise ValueError("No achievements found for this ID.")

    achievements = list(data["Achievements"].values())
    achievements.sort(key=lambda a: (int(a.get("DisplayOrder", 0)), int(a.get("ID", 0))))
    return achievements


def build_gauntlet_image(images, margin):
    rows = math.ceil(len(images) / GRID_COLUMNS)
    total_width = GRID_COLUMNS * BADGE_SIZE + (GRID_COLUMNS - 1) * margin
    total_height = rows * BADGE_SIZE + (rows - 1) * margin

    canvas = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    for index, img in enumerate(images):
        col_idx = index % GRID_COLUMNS
        row_idx = index // GRID_COLUMNS
        x = col_idx * (BADGE_SIZE + margin)
        y = row_idx * (BADGE_SIZE + margin)
        canvas.paste(img, (x, y))
    return canvas


def parse_margin(label):
    return int(label.replace("Margin:", "").replace("px", "").strip())


class BadgeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CheevosGrabber")
        self.geometry("450x600")
        apply_icon(self)

        # State variables
        self.saved_user = ""
        self.saved_key = ""
        self.save_dir = os.path.join(os.getcwd(), "badges")  # Default folder
        self.remember = False

        # Visual configuration
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.load_config()
        self.setup_ui()

    def setup_ui(self):
        self.auth_frame = ctk.CTkFrame(self)
        self.auth_frame.pack(pady=20, padx=20, fill="x")

        self.lbl_title = ctk.CTkLabel(self.auth_frame, text="API Authentication", font=("Arial", 16, "bold"))
        self.lbl_title.pack(pady=(10, 10))

        # Label and Entry for User
        self.lbl_user = ctk.CTkLabel(self.auth_frame, text="User (Web):", anchor="w")
        self.lbl_user.pack(padx=20, fill="x")
        self.ent_user = ctk.CTkEntry(self.auth_frame, placeholder_text="Ex: Carlos")
        self.ent_user.insert(0, self.saved_user)
        self.ent_user.pack(pady=(0, 10), padx=20, fill="x")

        # Label and Entry for API Key
        self.lbl_key = ctk.CTkLabel(self.auth_frame, text="Web API Key:", anchor="w")
        self.lbl_key.pack(padx=20, fill="x")
        self.ent_key = ctk.CTkEntry(self.auth_frame, placeholder_text="Enter your API Key", show="*")
        self.ent_key.insert(0, self.saved_key)
        self.ent_key.pack(pady=(0, 10), padx=20, fill="x")

        self.chk_remember_var = ctk.BooleanVar(value=self.remember)
        self.chk_remember = ctk.CTkCheckBox(self.auth_frame, text="Remember me", variable=self.chk_remember_var)
        self.chk_remember.pack(pady=(5, 15), padx=20, anchor="w")

        # Download frame
        self.dl_frame = ctk.CTkFrame(self)
        self.dl_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_dl = ctk.CTkLabel(self.dl_frame, text="Download", font=("Arial", 16, "bold"))
        self.lbl_dl.pack(pady=(10, 5))

        self.ent_game = ctk.CTkEntry(self.dl_frame, placeholder_text="Game ID (Ex: 1445)")
        self.ent_game.pack(pady=10, padx=20, fill="x")

        # Folder selection
        self.lbl_dir = ctk.CTkLabel(self.dl_frame, text="Save to folder:", anchor="w")
        self.lbl_dir.pack(padx=20, fill="x")

        self.dir_frame = ctk.CTkFrame(self.dl_frame, fg_color="transparent")
        self.dir_frame.pack(padx=20, pady=(0, 10), fill="x")

        self.ent_dir = ctk.CTkEntry(self.dir_frame)
        self.ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.update_dir_entry()

        self.btn_browse = ctk.CTkButton(self.dir_frame, text="Browse...", width=80, command=self.browse_folder)
        self.btn_browse.pack(side="right")

        # Action buttons
        self.btn_frame = ctk.CTkFrame(self.dl_frame, fg_color="transparent")
        self.btn_frame.pack(pady=15)

        self.btn_preview = ctk.CTkButton(self.btn_frame, text="Preview Template", width=120, fg_color="#E67E22", hover_color="#D35400", command=self.open_preview)
        self.btn_preview.pack(side="left", padx=5)

        self.btn_gauntlet = ctk.CTkButton(self.btn_frame, text="Create Gauntlet", width=120, fg_color="#8E44AD", hover_color="#732D91", command=self.create_gauntlet_template)
        self.btn_gauntlet.pack(side="left", padx=5)

        self.btn_download = ctk.CTkButton(self.btn_frame, text="Download Badges", width=120, command=self.start_download)
        self.btn_download.pack(side="right", padx=5)

        # Status
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.lbl_status.pack(pady=10)

    def update_status(self, text, color):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def update_dir_entry(self):
        self.ent_dir.configure(state="normal")
        self.ent_dir.delete(0, "end")
        self.ent_dir.insert(0, self.save_dir)
        self.ent_dir.configure(state="readonly")

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.save_dir)
        if selected_dir:
            self.save_dir = selected_dir
            self.update_dir_entry()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                self.saved_user = data.get("user", "")
                self.saved_key = data.get("api_key", "")
                self.save_dir = data.get("save_dir", self.save_dir)
                self.remember = data.get("remember", False)
            except Exception:
                pass

    def save_config(self):
        remember = self.chk_remember_var.get()
        data = {
            "save_dir": self.save_dir,
            "remember": remember,
            "user": self.ent_user.get().strip() if remember else "",
            "api_key": self.ent_key.get().strip() if remember else "",
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    def start_download(self):
        user = self.ent_user.get().strip()
        api_key = self.ent_key.get().strip()
        game_id = self.ent_game.get().strip()
        target_dir = self.ent_dir.get().strip()

        if not user or not api_key or not game_id:
            self.lbl_status.configure(text="Error: Fill in all fields!", text_color="red")
            return

        self.save_config()
        self.btn_download.configure(state="disabled")
        self.lbl_status.configure(text="Searching for achievement list...", text_color="white")

        threading.Thread(target=self.download_process, args=(user, api_key, game_id, target_dir), daemon=True).start()

    def download_process(self, user, api_key, game_id, target_dir):
        try:
            achievements = fetch_achievements(user, api_key, game_id)

            folder_name = os.path.join(target_dir, f"badges_{game_id}")
            os.makedirs(folder_name, exist_ok=True)

            total = len(achievements)
            for index, ach_data in enumerate(achievements, start=1):
                badge_name = ach_data.get("BadgeName")
                if badge_name:
                    img_res = requests.get(BADGE_URL.format(badge_name), timeout=REQUEST_TIMEOUT)
                    if img_res.status_code == 200:
                        # Numeric prefix keeps the site's order in the file explorer
                        file_name = f"{index:03d}_{badge_name}.png"
                        with open(os.path.join(folder_name, file_name), "wb") as f:
                            f.write(img_res.content)

                self.update_status(f"Downloading badges: {index}/{total}...", "white")

            self.update_status(f"Completed! Saved to:\n{folder_name}", "green")

        except ValueError as e:
            self.update_status(str(e), "red")
        except Exception as e:
            self.update_status(f"Unexpected error: {e}", "red")
        finally:
            self.after(0, lambda: self.btn_download.configure(state="normal"))

    def open_preview(self):
        user = self.ent_user.get().strip()
        api_key = self.ent_key.get().strip()
        game_id = self.ent_game.get().strip()

        if not user or not api_key or not game_id:
            self.lbl_status.configure(text="Error: Fill in the fields to preview!", text_color="red")
            return

        preview_win = ctk.CTkToplevel(self)
        preview_win.title(f"Game Template {game_id}")
        preview_win.geometry("800x600")
        apply_icon(preview_win)
        preview_win.grab_set()

        # Top bar with controls (margin and save)
        ctrl_frame = ctk.CTkFrame(preview_win)
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        margin_var = ctk.StringVar(value=MARGIN_OPTIONS[0])
        opt_margin = ctk.CTkOptionMenu(ctrl_frame, values=MARGIN_OPTIONS, variable=margin_var, state="disabled")
        opt_margin.pack(side="left", padx=10)

        btn_save = ctk.CTkButton(ctrl_frame, text="Save Template", fg_color="#27AE60", hover_color="#2ECC71", state="disabled")
        btn_save.pack(side="right", padx=10)

        # Image area
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        lbl_loading = ctk.CTkLabel(scroll_frame, text="Downloading badges from the API into memory...", font=("Arial", 14))
        lbl_loading.pack(pady=20)

        img_label = ctk.CTkLabel(scroll_frame, text="")

        # State local to this window
        state = {"images": [], "result": None}

        def update_preview(selected_margin):
            if not state["images"]:
                return
            template_img = build_gauntlet_image(state["images"], parse_margin(selected_margin))
            state["result"] = template_img

            ctk_img = ctk.CTkImage(light_image=template_img, dark_image=template_img, size=template_img.size)
            img_label.configure(image=ctk_img)
            img_label.image = ctk_img

        def save_image():
            if state["result"] is None:
                return
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"template_game_{game_id}.png",
                initialdir=self.save_dir,
                title="Save Final Template",
                filetypes=[("PNG", "*.png")],
            )
            if save_path:
                state["result"].save(save_path)
                self.update_status("Template saved successfully!", "green")
                preview_win.destroy()
                try:
                    os.startfile(save_path)  # Windows only
                except Exception:
                    pass

        opt_margin.configure(command=update_preview)
        btn_save.configure(command=save_image)

        def show_error(message):
            self.after(0, lambda: lbl_loading.configure(text=message, text_color="red"))

        def finalize_load(loaded_images):
            state["images"] = loaded_images
            lbl_loading.destroy()
            img_label.pack(pady=10)
            opt_margin.configure(state="normal")
            btn_save.configure(state="normal")
            update_preview(margin_var.get())

        def worker():
            try:
                achievements = fetch_achievements(user, api_key, game_id)
                loaded_images = []
                for ach_data in achievements:
                    badge_name = ach_data.get("BadgeName")
                    if not badge_name:
                        continue
                    img_res = requests.get(BADGE_URL.format(badge_name), timeout=REQUEST_TIMEOUT)
                    if img_res.status_code == 200:
                        img = Image.open(io.BytesIO(img_res.content)).convert("RGBA")
                        loaded_images.append(img.resize((BADGE_SIZE, BADGE_SIZE)))
                self.after(0, lambda: finalize_load(loaded_images))
            except ValueError as e:
                show_error(str(e))
            except Exception as e:
                show_error(f"Error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def create_gauntlet_template(self):
        file_paths = filedialog.askopenfilenames(
            title="Select badges for the template",
            initialdir=self.save_dir,
            filetypes=[("PNG Images", "*.png")],
        )
        if not file_paths:
            return

        try:
            # Natural sorting to respect 1.png, 2.png, 10.png, etc.
            def numerical_sort_key(filepath):
                filename = os.path.basename(filepath)
                return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", filename)]

            file_paths = sorted(file_paths, key=numerical_sort_key)
            self.show_gauntlet_preview(file_paths)

        except Exception as e:
            self.update_status(f"Error loading files: {e}", "red")

    def show_gauntlet_preview(self, file_paths):
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("Gauntlet Preview")
        preview_win.geometry("800x600")
        apply_icon(preview_win)
        preview_win.grab_set()

        # Top bar with controls (margin and save)
        ctrl_frame = ctk.CTkFrame(preview_win)
        ctrl_frame.pack(fill="x", padx=10, pady=10)

        # Scrollable frame (useful for games with hundreds of achievements)
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        img_label = ctk.CTkLabel(scroll_frame, text="")
        img_label.pack(pady=10)

        # Load the images once; only the layout is rebuilt when the margin changes
        images = [Image.open(fp).convert("RGBA").resize((BADGE_SIZE, BADGE_SIZE)) for fp in file_paths]
        state = {"result": None}

        def update_preview(selected_margin):
            template_img = build_gauntlet_image(images, parse_margin(selected_margin))
            state["result"] = template_img

            ctk_img = ctk.CTkImage(light_image=template_img, dark_image=template_img, size=template_img.size)
            img_label.configure(image=ctk_img)
            img_label.image = ctk_img

        margin_var = ctk.StringVar(value=MARGIN_OPTIONS[0])
        opt_margin = ctk.CTkOptionMenu(ctrl_frame, values=MARGIN_OPTIONS, variable=margin_var, command=update_preview)
        opt_margin.pack(side="left", padx=10)

        def save_image():
            if state["result"] is None:
                return
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile="gauntlet_template.png",
                initialdir=self.save_dir,
                title="Save Final Template",
                filetypes=[("PNG", "*.png")],
            )
            if save_path:
                state["result"].save(save_path)
                self.update_status("Template saved successfully!", "green")
                preview_win.destroy()
                try:
                    os.startfile(save_path)  # Windows only
                except Exception:
                    pass

        btn_save = ctk.CTkButton(ctrl_frame, text="Save Template", fg_color="#27AE60", hover_color="#2ECC71", command=save_image)
        btn_save.pack(side="right", padx=10)

        # First render at 0px as soon as the window opens
        update_preview(margin_var.get())


if __name__ == "__main__":
    app = BadgeDownloaderApp()
    app.mainloop()