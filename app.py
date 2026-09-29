from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
import threading
import requests
import json
import math
import os
import io

# API Configurations
API_URL = "https://retroachievements.org/API/API_GetGameExtended.php"
BADGE_URL = "https://media.retroachievements.org/Badge/{}.png"
CONFIG_FILE = "config.json"

class BadgeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CheevosGrabber") 
        self.geometry("450x600")
        
        # State variables
        self.saved_user = ""
        self.saved_key = ""
        self.save_dir = os.path.join(os.getcwd(), "badges") # Default folder
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

        # Download Frame
        self.dl_frame = ctk.CTkFrame(self)
        self.dl_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_dl = ctk.CTkLabel(self.dl_frame, text="Download", font=("Arial", 16, "bold"))
        self.lbl_dl.pack(pady=(10, 5))

        self.ent_game = ctk.CTkEntry(self.dl_frame, placeholder_text="Game ID (Ex: 1445)")
        self.ent_game.pack(pady=10, padx=20, fill="x")

        # Folder Selection Section
        self.lbl_dir = ctk.CTkLabel(self.dl_frame, text="Save to folder:", anchor="w")
        self.lbl_dir.pack(padx=20, fill="x")

        self.dir_frame = ctk.CTkFrame(self.dl_frame, fg_color="transparent")
        self.dir_frame.pack(padx=20, pady=(0, 10), fill="x")

        self.ent_dir = ctk.CTkEntry(self.dir_frame)
        self.ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.update_dir_entry()

        self.btn_browse = ctk.CTkButton(self.dir_frame, text="Browse...", width=80, command=self.browse_folder)
        self.btn_browse.pack(side="right")

        # Action Buttons
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
        data = {
            "save_dir": self.save_dir,
            "remember": self.chk_remember_var.get()
        }
        
        if self.chk_remember_var.get():
            data["user"] = self.ent_user.get().strip()
            data["api_key"] = self.ent_key.get().strip()
        else:
            data["user"] = ""
            data["api_key"] = ""
            
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
            params = {"z": user, "y": api_key, "i": game_id}
            response = requests.get(API_URL, params=params)
            
            if response.status_code != 200:
                self.update_status("API Error. Are the credentials correct?", "red")
                return
            
            data = response.json()
            if "Achievements" not in data or not data["Achievements"]:
                self.update_status("No achievements found for this ID.", "red")
                return
            
            achievements_list = list(data["Achievements"].values())
            achievements_list.sort(key=lambda x: (int(x.get("DisplayOrder", 0)), int(x.get("ID", 0))))

            folder_name = os.path.join(target_dir, f"badges_{game_id}")
            os.makedirs(folder_name, exist_ok=True)

            total = len(achievements_list)
            count = 0

            for index, ach_data in enumerate(achievements_list, start=1):
                badge_name = ach_data.get("BadgeName")
                if badge_name:
                    img_url = BADGE_URL.format(badge_name)
                    img_res = requests.get(img_url)
                    
                    if img_res.status_code == 200:
                        # Adds a numeric prefix to enforce order in the file explorer
                        file_name = f"{index:03d}_{badge_name}.png"
                        save_path = os.path.join(folder_name, file_name)
                        with open(save_path, "wb") as f:
                            f.write(img_res.content)
                
                count += 1
                self.update_status(f"Downloading badges: {count}/{total}...", "white")

            self.update_status(f"Completed! Saved to:\n{folder_name}", "green")

        except Exception as e:
            self.update_status(f"Unexpected error: {str(e)}", "red")
        finally:
            self.after(0, lambda: self.btn_download.configure(state="normal"))

    def update_status(self, text, color):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def open_preview(self):
        user = self.ent_user.get().strip()
        api_key = self.ent_key.get().strip()
        game_id = self.ent_game.get().strip()

        if not user or not api_key or not game_id:
            self.lbl_status.configure(text="Error: Fill in the fields to preview!", text_color="red")
            return

        # Creates the preview window
        preview_win = ctk.CTkToplevel(self)
        preview_win.title(f"Game Template {game_id}")
        preview_win.geometry("700x500")
        preview_win.grab_set()

        # Scrollable frame for the image grid
        scroll_frame = ctk.CTkScrollableFrame(preview_win, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        lbl_loading = ctk.CTkLabel(scroll_frame, text="Loading template into memory...", font=("Arial", 14))
        lbl_loading.grid(row=0, column=0, pady=20)

        # Starts the loading thread
        threading.Thread(target=self.load_preview_data, args=(user, api_key, game_id, scroll_frame, lbl_loading), daemon=True).start()

    def load_preview_data(self, user, api_key, game_id, scroll_frame, lbl_loading):
        try:
            params = {"z": user, "y": api_key, "i": game_id}
            response = requests.get(API_URL, params=params)
            
            if response.status_code != 200:
                self.after(0, lambda: lbl_loading.configure(text="API Error. Invalid credentials?", text_color="red"))
                return
            
            data = response.json()
            if "Achievements" not in data or not data["Achievements"]:
                self.after(0, lambda: lbl_loading.configure(text="No achievements found.", text_color="red"))
                return

            achievements_list = list(data["Achievements"].values())
            achievements_list.sort(key=lambda x: (int(x.get("DisplayOrder", 0)), int(x.get("ID", 0))))

            self.after(0, lambda: lbl_loading.destroy())

            columns = 10
            row = 0
            col = 0

            for ach_data in achievements_list:
                badge_name = ach_data.get("BadgeName")
                if badge_name:
                    img_url = BADGE_URL.format(badge_name)
                    img_res = requests.get(img_url)
                    
                    if img_res.status_code == 200:
                        image_data = Image.open(io.BytesIO(img_res.content))
                        ctk_img = ctk.CTkImage(light_image=image_data, dark_image=image_data, size=(64, 64))
                        
                        self.after(0, self.add_image_to_grid, scroll_frame, ctk_img, row, col)
                        
                        col += 1
                        if col >= columns:
                            col = 0
                            row += 1

        except Exception as e:
            self.after(0, lambda: lbl_loading.configure(text=f"Error: {str(e)}", text_color="red"))

    def add_image_to_grid(self, frame, ctk_img, row, col):
        lbl = ctk.CTkLabel(frame, image=ctk_img, text="")
        lbl.grid(row=row, column=col, padx=0, pady=0)

    def create_gauntlet_template(self):
        # Opens window for the user to select the downloaded icons
        file_paths = filedialog.askopenfilenames(
            title="Select badges for the template",
            initialdir=self.save_dir,
            filetypes=[("PNG Images", "*.png")]
        )

        if not file_paths:
            return

        try:
            # Sorts selected files alphabetically to respect order (e.g., 001_, 002_)
            file_paths = sorted(file_paths)

            columns = 10
            rows = math.ceil(len(file_paths) / columns)

            template_img = Image.new('RGBA', (columns * 64, rows * 64), (0, 0, 0, 0))

            for index, file_path in enumerate(file_paths):
                img = Image.open(file_path).convert("RGBA")
                img = img.resize((64, 64))
                x = (index % columns) * 64
                y = (index // columns) * 64
                
                template_img.paste(img, (x, y))

            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile="gauntlet_template.png",
                initialdir=self.save_dir,
                title="Save Final Template",
                filetypes=[("PNG", "*.png")]
            )

            if save_path:
                template_img.save(save_path)
                self.update_status(f"Gauntlet template saved successfully!", "green")

                try:
                    os.startfile(save_path)
                except Exception:
                    pass 

        except Exception as e:
            self.update_status(f"Error creating template: {str(e)}", "red")

if __name__ == "__main__":
    app = BadgeDownloaderApp()
    app.mainloop()