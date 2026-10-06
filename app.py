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
MEDIA_BASE_URL = "https://media.retroachievements.org{}"
CONFIG_FILE = "config.json"

# Gauntlet layout
BADGE_SIZE = 64
GRID_COLUMNS = 10
MARGIN_OPTIONS = ["Margin: 0px", "Margin: 1px", "Margin: 2px", "Margin: 4px"]
REQUEST_TIMEOUT = 30

# 🎨 Centralized color palette
COLORS = {
    "bg_primary": "#1a1a1a",
    "bg_secondary": "#242424",
    "bg_card": "#2b2b2b",
    "accent": "#3B8ED0",
    "accent_hover": "#36719F",
    "success": "#27AE60",
    "success_hover": "#2ECC71",
    "warning": "#E67E22",
    "warning_hover": "#D35400",
    "purple": "#8E44AD",
    "purple_hover": "#732D91",
    "danger": "#E74C3C",
    "text_muted": "#8a8a8a",
    "border": "#3a3a3a",
}


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


def fetch_achievements(user, api_key, game_id, set_type="Official"):
    f_value = 5 if set_type == "Unofficial" else 3
    params = {"z": user, "y": api_key, "i": game_id, "f": f_value}

    response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)

    if response.status_code != 200:
        raise ValueError("API Error. Are the credentials correct?")

    data = response.json()
    if "Achievements" not in data or not data["Achievements"]:
        raise ValueError("No achievements found for this ID and Set Type.")

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
        self.geometry("960x640")
        self.minsize(880, 600)
        self.configure(fg_color=COLORS["bg_primary"])

        # State
        self.saved_user = ""
        self.saved_key = ""
        self.save_dir = os.path.join(os.getcwd(), "badges")
        self.remember = False
        self.current_achievements = []  # cache of loaded achievements

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.load_config()
        self.setup_ui()
        apply_icon(self)

    # MAIN UI
    def setup_ui(self):
        # Main grid: sidebar (left) + content (right)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    # ─────────────── SIDEBAR ───────────────
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=COLORS["bg_secondary"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(6, weight=1)

        # Logo / Title
        logo = ctk.CTkLabel(
            sidebar, text="CheevosGrabber",
            font=("Arial", 20, "bold"), anchor="w"
        )
        logo.grid(row=0, column=0, padx=20, pady=(25, 5), sticky="w")

        subtitle = ctk.CTkLabel(
            sidebar, text="RetroAchievements Badge Tool",
            font=("Arial", 11), text_color=COLORS["text_muted"], anchor="w"
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Separator
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).grid(
            row=2, column=0, sticky="ew", padx=15, pady=(0, 15)
        )

        # Credentials section
        ctk.CTkLabel(
            sidebar, text="CREDENTIALS", font=("Arial", 10, "bold"),
            text_color=COLORS["text_muted"], anchor="w"
        ).grid(row=3, column=0, padx=20, pady=(0, 8), sticky="w")

        self.ent_user = ctk.CTkEntry(
            sidebar, placeholder_text="RA Username", height=36
        )
        self.ent_user.grid(row=4, column=0, padx=20, pady=(0, 8), sticky="ew")
        if self.saved_user:
            self.ent_user.insert(0, self.saved_user)

        self.ent_key = ctk.CTkEntry(
            sidebar, placeholder_text="Web API Key", show="*", height=36
        )
        self.ent_key.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="ew")
        if self.saved_key:
            self.ent_key.insert(0, self.saved_key)

        self.chk_remember_var = ctk.BooleanVar(value=self.remember)
        ctk.CTkCheckBox(
            sidebar, text="Remember credentials",
            variable=self.chk_remember_var, font=("Arial", 11)
        ).grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nw")

        # Sidebar footer
        footer = ctk.CTkLabel(
            sidebar, text="v1.0 • Made for the RA community",
            font=("Arial", 10), text_color=COLORS["text_muted"]
        )
        footer.grid(row=7, column=0, padx=20, pady=15, sticky="sw")

    # ─────────────── MAIN AREA ───────────────
    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        ctk.CTkLabel(
            header, text="Search Game", font=("Arial", 22, "bold"), anchor="w"
        ).pack(side="left")

        # ── Card: Search + Game Info ──
        search_card = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=12)
        search_card.grid(row=1, column=0, sticky="nsew")
        search_card.grid_columnconfigure(0, weight=1)

        # Search row
        search_row = ctk.CTkFrame(search_card, fg_color="transparent")
        search_row.pack(fill="x", padx=20, pady=(20, 15))

        ctk.CTkLabel(
            search_row, text="Game ID:", font=("Arial", 13, "bold")
        ).pack(side="left", padx=(0, 10))

        self.ent_game = ctk.CTkEntry(
            search_row, placeholder_text="Ex: 1445", height=38, width=200
        )
        self.ent_game.pack(side="left", padx=(0, 10))

        self.btn_search = ctk.CTkButton(
            search_row, text="Search", width=120, height=38,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self.fetch_game_info
        )
        self.btn_search.pack(side="left")

        # Set type on the right
        type_frame = ctk.CTkFrame(search_row, fg_color="transparent")
        type_frame.pack(side="right")

        ctk.CTkLabel(
            type_frame, text="Set:", font=("Arial", 13, "bold")
        ).pack(side="left", padx=(0, 8))

        self.type_var = ctk.StringVar(value="Official")
        ctk.CTkOptionMenu(
            type_frame, values=["Official", "Unofficial"],
            variable=self.type_var, width=130, height=38
        ).pack(side="left")

        # ── Game Info (icon + title) ──
        self.info_card = ctk.CTkFrame(
            search_card, fg_color=COLORS["bg_secondary"], corner_radius=10
        )
        self.info_card.pack(fill="x", padx=20, pady=(0, 20))

        self.lbl_game_icon = ctk.CTkLabel(
            self.info_card, text="?", font=("Arial", 32),
            width=96, height=96, fg_color="#1f1f1f", corner_radius=8
        )
        self.lbl_game_icon.pack(side="left", padx=15, pady=15)

        title_box = ctk.CTkFrame(self.info_card, fg_color="transparent")
        title_box.pack(side="left", padx=10, pady=15, fill="both", expand=True)

        ctk.CTkLabel(
            title_box, text="CURRENT GAME", font=("Arial", 10, "bold"),
            text_color=COLORS["text_muted"], anchor="w"
        ).pack(anchor="w")

        self.lbl_game_title = ctk.CTkLabel(
            title_box, text="No game loaded",
            font=("Arial", 16, "bold"), anchor="w", justify="left",
            wraplength=500
        )
        self.lbl_game_title.pack(anchor="w", pady=(2, 0))

        self.lbl_ach_count = ctk.CTkLabel(
            title_box, text="", font=("Arial", 11),
            text_color=COLORS["text_muted"], anchor="w"
        )
        self.lbl_ach_count.pack(anchor="w", pady=(4, 0))

        # ── Card: Actions ──
        actions_card = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=12)
        actions_card.grid(row=2, column=0, sticky="ew", pady=(15, 0))

        # Destination folder
        dir_row = ctk.CTkFrame(actions_card, fg_color="transparent")
        dir_row.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(
            dir_row, text="Destination folder:", font=("Arial", 12, "bold")
        ).pack(side="left", padx=(0, 10))

        self.ent_dir = ctk.CTkEntry(dir_row, height=34)
        self.ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.update_dir_entry()

        ctk.CTkButton(
            dir_row, text="Browse", width=90, height=34,
            fg_color="transparent", border_width=1,
            border_color=COLORS["border"], hover_color=COLORS["bg_secondary"],
            command=self.browse_folder
        ).pack(side="right")

        # Separator
        ctk.CTkFrame(actions_card, height=1, fg_color=COLORS["border"]).pack(
            fill="x", padx=20, pady=5
        )

        # Action buttons
        btn_row = ctk.CTkFrame(actions_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(10, 15))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="btn")

        self.btn_preview = ctk.CTkButton(
            btn_row, text="Preview Template", height=44,
            fg_color=COLORS["warning"], hover_color=COLORS["warning_hover"],
            font=("Arial", 13, "bold"), command=self.open_preview
        )
        self.btn_preview.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_gauntlet = ctk.CTkButton(
            btn_row, text="Create Gauntlet", height=44,
            fg_color=COLORS["purple"], hover_color=COLORS["purple_hover"],
            font=("Arial", 13, "bold"), command=self.create_gauntlet_template
        )
        self.btn_gauntlet.grid(row=0, column=1, padx=6, sticky="ew")

        self.btn_download = ctk.CTkButton(
            btn_row, text="Download Badges", height=44,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            font=("Arial", 13, "bold"), command=self.start_download
        )
        self.btn_download.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        # ── Card: Status / Progress ──
        self.status_card = ctk.CTkFrame(
            main, fg_color=COLORS["bg_card"], corner_radius=12
        )
        self.status_card.grid(row=3, column=0, sticky="ew", pady=(15, 0))

        status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=20, pady=15)

        self.lbl_status = ctk.CTkLabel(
            status_inner, text="Ready to start.",
            font=("Arial", 12), anchor="w", justify="left"
        )
        self.lbl_status.pack(fill="x")

        # Progress bar (hidden initially)
        self.progress = ctk.CTkProgressBar(
            status_inner, height=8, corner_radius=4,
            progress_color=COLORS["accent"]
        )
        self.progress.set(0)

    # LOGIC
    def fetch_game_info(self):
        user = self.ent_user.get().strip()
        api_key = self.ent_key.get().strip()
        game_id = self.ent_game.get().strip()

        if not user or not api_key or not game_id:
            self.update_status("Please fill in username, API key, and Game ID.", COLORS["danger"])
            return

        self.lbl_game_title.configure(text="Searching...", text_color=COLORS["text_muted"])
        self.lbl_ach_count.configure(text="")
        self.lbl_game_icon.configure(image=None, text="...")
        self.btn_search.configure(state="disabled")
        self.update_status("Querying API...", COLORS["text_muted"])

        threading.Thread(
            target=self._fetch_game_info_worker,
            args=(user, api_key, game_id), daemon=True
        ).start()

    def _fetch_game_info_worker(self, user, api_key, game_id):
        try:
            params = {"z": user, "y": api_key, "i": game_id}
            response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code != 200:
                raise ValueError("API Error.")

            data = response.json()
            title = data.get("Title", "Unknown Game")
            icon_path = data.get("ImageIcon")
            num_ach = len(data.get("Achievements", {}))

            img_data = None
            if icon_path:
                img_url = MEDIA_BASE_URL.format(icon_path)
                img_res = requests.get(img_url, timeout=REQUEST_TIMEOUT)
                if img_res.status_code == 200:
                    img_data = Image.open(io.BytesIO(img_res.content)).convert("RGBA")

            self.after(0, lambda: self._update_game_info_ui(title, img_data, num_ach))
            self.update_status(f"✓  '{title}' loaded successfully.", COLORS["success"])

        except Exception as e:
            self.after(0, lambda: self._update_game_info_ui("Error loading game", None, 0))
            self.update_status(f"✗  Error: {str(e)}", COLORS["danger"])
        finally:
            self.after(0, lambda: self.btn_search.configure(state="normal"))

    def _update_game_info_ui(self, title, img_data, num_ach):
        self.lbl_game_title.configure(text=title, text_color="white")
        if num_ach:
            self.lbl_ach_count.configure(text=f"{num_ach} achievements available")
        if img_data:
            ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(96, 96))
            self.lbl_game_icon.configure(image=ctk_img, text="", fg_color="transparent")
            self.lbl_game_icon.image = ctk_img
        else:
            self.lbl_game_icon.configure(image=None, text="✗", fg_color="#1f1f1f")

    def update_status(self, text, color=None):
        self.after(0, lambda: self.lbl_status.configure(
            text=text, text_color=color or "white"
        ))

    def _show_progress(self, show=True):
        if show:
            self.progress.pack(fill="x", pady=(10, 0))
        else:
            self.progress.pack_forget()

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
        set_type = self.type_var.get()

        if not user or not api_key or not game_id:
            self.update_status("Please fill in all credentials and the Game ID.", COLORS["danger"])
            return

        self.save_config()
        self.btn_download.configure(state="disabled")
        self.update_status("Fetching achievement list...", COLORS["text_muted"])
        self.progress.set(0)
        self._show_progress(True)

        threading.Thread(
            target=self.download_process,
            args=(user, api_key, game_id, target_dir, set_type), daemon=True
        ).start()

    def download_process(self, user, api_key, game_id, target_dir, set_type):
        try:
            achievements = fetch_achievements(user, api_key, game_id, set_type)
            folder_name = os.path.join(target_dir, f"badges_{game_id}_{set_type.lower()}")
            os.makedirs(folder_name, exist_ok=True)

            total = len(achievements)
            for index, ach_data in enumerate(achievements, start=1):
                badge_name = ach_data.get("BadgeName")
                if badge_name:
                    img_res = requests.get(BADGE_URL.format(badge_name), timeout=REQUEST_TIMEOUT)
                    if img_res.status_code == 200:
                        file_name = f"{index:03d}_{badge_name}.png"
                        with open(os.path.join(folder_name, file_name), "wb") as f:
                            f.write(img_res.content)

                progress_val = index / total
                self.after(0, lambda v=progress_val: self.progress.set(v))
                self.update_status(f"⬇  Downloading badges... {index}/{total}", "white")

            self.update_status(f"Completed! Saved to: {folder_name}", COLORS["success"])

        except ValueError as e:
            self.update_status(f"{str(e)}", COLORS["danger"])
        except Exception as e:
            self.update_status(f"Unexpected error: {e}", COLORS["danger"])
        finally:
            self.after(0, lambda: self.btn_download.configure(state="normal"))
            self.after(2500, lambda: self._show_progress(False))

    # PREVIEW (game template)
    def open_preview(self):
        user = self.ent_user.get().strip()
        api_key = self.ent_key.get().strip()
        game_id = self.ent_game.get().strip()
        set_type = self.type_var.get()

        if not user or not api_key or not game_id:
            self.update_status("Please fill in credentials and Game ID for preview.", COLORS["danger"])
            return

        preview_win = ctk.CTkToplevel(self)
        preview_win.title(f"Preview — Game {game_id} ({set_type})")
        preview_win.geometry("880x640")
        preview_win.configure(fg_color=COLORS["bg_primary"])
        apply_icon(preview_win)
        preview_win.grab_set()

        ctrl_frame = ctk.CTkFrame(preview_win, fg_color=COLORS["bg_card"], corner_radius=12)
        ctrl_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            ctrl_frame, text="Adjustments", font=("Arial", 14, "bold")
        ).pack(side="left", padx=20, pady=15)

        margin_var = ctk.StringVar(value=MARGIN_OPTIONS[0])
        opt_margin = ctk.CTkOptionMenu(
            ctrl_frame, values=MARGIN_OPTIONS, variable=margin_var,
            state="disabled", width=150, height=36
        )
        opt_margin.pack(side="left", padx=10, pady=15)

        btn_save = ctk.CTkButton(
            ctrl_frame, text="Save Template", height=36,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            state="disabled"
        )
        btn_save.pack(side="right", padx=20, pady=15)

        scroll_frame = ctk.CTkScrollableFrame(
            preview_win, fg_color=COLORS["bg_secondary"], corner_radius=10
        )
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        lbl_loading = ctk.CTkLabel(
            scroll_frame, text="Fetching badges from API...",
            font=("Arial", 14), text_color=COLORS["text_muted"]
        )
        lbl_loading.pack(pady=40)

        img_label = ctk.CTkLabel(scroll_frame, text="")

        state = {"images": [], "result": None}

        def update_preview(selected_margin):
            if not state["images"]:
                return
            template_img = build_gauntlet_image(state["images"], parse_margin(selected_margin))
            state["result"] = template_img
            ctk_img = ctk.CTkImage(
                light_image=template_img, dark_image=template_img,
                size=template_img.size
            )
            img_label.configure(image=ctk_img)
            img_label.image = ctk_img

        def save_image():
            if state["result"] is None:
                return
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"template_game_{game_id}_{set_type.lower()}.png",
                initialdir=self.save_dir,
                title="Save Template",
                filetypes=[("PNG", "*.png")],
            )
            if save_path:
                state["result"].save(save_path)
                self.update_status("✓  Template saved successfully!", COLORS["success"])
                preview_win.destroy()
                try:
                    os.startfile(save_path)
                except Exception:
                    pass

        opt_margin.configure(command=update_preview)
        btn_save.configure(command=save_image)

        def finalize_load(loaded_images):
            state["images"] = loaded_images
            lbl_loading.destroy()
            img_label.pack(pady=20)
            opt_margin.configure(state="normal")
            btn_save.configure(state="normal")
            update_preview(margin_var.get())

        def worker():
            try:
                achievements = fetch_achievements(user, api_key, game_id, set_type)
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
            except Exception as e:
                self.after(0, lambda: lbl_loading.configure(
                    text=f"✗  Error: {e}", text_color=COLORS["danger"]
                ))

        threading.Thread(target=worker, daemon=True).start()

    # GAUNTLET (local files)
    def create_gauntlet_template(self):
        file_paths = filedialog.askopenfilenames(
            title="Select badges for the template",
            initialdir=self.save_dir,
            filetypes=[("PNG Images", "*.png")],
        )
        if not file_paths:
            return

        try:
            def numerical_sort_key(filepath):
                filename = os.path.basename(filepath)
                return [int(t) if t.isdigit() else t.lower()
                        for t in re.split(r"(\d+)", filename)]

            file_paths = sorted(file_paths, key=numerical_sort_key)
            self.show_gauntlet_preview(file_paths)

        except Exception as e:
            self.update_status(f"✗  Error loading files: {e}", COLORS["danger"])

    def show_gauntlet_preview(self, file_paths):
        preview_win = ctk.CTkToplevel(self)
        preview_win.title("Preview — Gauntlet")
        preview_win.geometry("880x640")
        preview_win.configure(fg_color=COLORS["bg_primary"])
        apply_icon(preview_win)
        preview_win.grab_set()

        ctrl_frame = ctk.CTkFrame(preview_win, fg_color=COLORS["bg_card"], corner_radius=12)
        ctrl_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            ctrl_frame, text="⚔  Gauntlet", font=("Arial", 14, "bold")
        ).pack(side="left", padx=20, pady=15)

        margin_var = ctk.StringVar(value=MARGIN_OPTIONS[0])
        opt_margin = ctk.CTkOptionMenu(
            ctrl_frame, values=MARGIN_OPTIONS, variable=margin_var,
            width=150, height=36
        )
        opt_margin.pack(side="left", padx=10, pady=15)

        scroll_frame = ctk.CTkScrollableFrame(
            preview_win, fg_color=COLORS["bg_secondary"], corner_radius=10
        )
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        img_label = ctk.CTkLabel(scroll_frame, text="")
        img_label.pack(pady=20)

        images = [Image.open(fp).convert("RGBA").resize((BADGE_SIZE, BADGE_SIZE))
                  for fp in file_paths]
        state = {"result": None}

        def update_preview(selected_margin):
            template_img = build_gauntlet_image(images, parse_margin(selected_margin))
            state["result"] = template_img
            ctk_img = ctk.CTkImage(
                light_image=template_img, dark_image=template_img,
                size=template_img.size
            )
            img_label.configure(image=ctk_img)
            img_label.image = ctk_img

        def save_image():
            if state["result"] is None:
                return
            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile="gauntlet_template.png",
                initialdir=self.save_dir,
                title="Save Template",
                filetypes=[("PNG", "*.png")],
            )
            if save_path:
                state["result"].save(save_path)
                self.update_status("Template saved successfully!", COLORS["success"])
                preview_win.destroy()
                try:
                    os.startfile(save_path)
                except Exception:
                    pass

        ctk.CTkButton(
            ctrl_frame, text="Save Template", height=36,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            command=save_image
        ).pack(side="right", padx=20, pady=15)

        opt_margin.configure(command=update_preview)
        update_preview(margin_var.get())


if __name__ == "__main__":
    app = BadgeDownloaderApp()
    app.mainloop()