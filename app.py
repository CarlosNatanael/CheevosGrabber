import customtkinter as ctk
from tkinter import filedialog
import requests
import os
import json
import threading

# Configurações da API
API_URL = "https://retroachievements.org/API/API_GetGameExtended.php"
BADGE_URL = "https://media.retroachievements.org/Badge/{}.png"
CONFIG_FILE = "config.json"

class BadgeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Pode alterar o nome depois, deixei uma sugestão integrada
        self.title("CheevosGrabber") 
        self.geometry("450x600")
        
        # Variáveis de estado
        self.saved_user = ""
        self.saved_key = ""
        self.save_dir = os.path.join(os.getcwd(), "badges") # Pasta padrão
        self.remember = False
        
        # Configuração visual
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.load_config()
        self.setup_ui()

    def setup_ui(self):
        # 1. Frame de Autenticação
        self.auth_frame = ctk.CTkFrame(self)
        self.auth_frame.pack(pady=20, padx=20, fill="x")

        self.lbl_title = ctk.CTkLabel(self.auth_frame, text="Autenticação API", font=("Arial", 16, "bold"))
        self.lbl_title.pack(pady=(10, 10))

        # Label e Entry para o Utilizador
        self.lbl_user = ctk.CTkLabel(self.auth_frame, text="Utilizador (Web):", anchor="w")
        self.lbl_user.pack(padx=20, fill="x")
        self.ent_user = ctk.CTkEntry(self.auth_frame, placeholder_text="Ex: Carlos")
        self.ent_user.insert(0, self.saved_user)
        self.ent_user.pack(pady=(0, 10), padx=20, fill="x")

        # Label e Entry para a Chave API
        self.lbl_key = ctk.CTkLabel(self.auth_frame, text="Chave API Web:", anchor="w")
        self.lbl_key.pack(padx=20, fill="x")
        self.ent_key = ctk.CTkEntry(self.auth_frame, placeholder_text="Insira a sua API Key", show="*")
        self.ent_key.insert(0, self.saved_key)
        self.ent_key.pack(pady=(0, 10), padx=20, fill="x")

        self.chk_remember_var = ctk.BooleanVar(value=self.remember)
        self.chk_remember = ctk.CTkCheckBox(self.auth_frame, text="Lembrar-me", variable=self.chk_remember_var)
        self.chk_remember.pack(pady=(5, 15), padx=20, anchor="w")

        # 2. Frame de Download
        self.dl_frame = ctk.CTkFrame(self)
        self.dl_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_dl = ctk.CTkLabel(self.dl_frame, text="Download", font=("Arial", 16, "bold"))
        self.lbl_dl.pack(pady=(10, 5))

        self.ent_game = ctk.CTkEntry(self.dl_frame, placeholder_text="ID do Jogo (Ex: 1445)")
        self.ent_game.pack(pady=10, padx=20, fill="x")

        # Secção de Escolha de Pasta
        self.lbl_dir = ctk.CTkLabel(self.dl_frame, text="Guardar na pasta:", anchor="w")
        self.lbl_dir.pack(padx=20, fill="x")

        self.dir_frame = ctk.CTkFrame(self.dl_frame, fg_color="transparent")
        self.dir_frame.pack(padx=20, pady=(0, 10), fill="x")

        self.ent_dir = ctk.CTkEntry(self.dir_frame)
        self.ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.update_dir_entry() # Preenche com a pasta guardada no config

        self.btn_browse = ctk.CTkButton(self.dir_frame, text="Procurar...", width=80, command=self.browse_folder)
        self.btn_browse.pack(side="right")

        # Botão Principal
        self.btn_download = ctk.CTkButton(self.dl_frame, text="Baixar Badges", command=self.start_download)
        self.btn_download.pack(pady=15)

        # 3. Status
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
            self.lbl_status.configure(text="Erro: Preencha todos os campos!", text_color="red")
            return

        self.save_config()
        self.btn_download.configure(state="disabled")
        self.lbl_status.configure(text="A procurar lista de conquistas...", text_color="white")

        threading.Thread(target=self.download_process, args=(user, api_key, game_id, target_dir), daemon=True).start()

    def download_process(self, user, api_key, game_id, target_dir):
        try:
            params = {"z": user, "y": api_key, "i": game_id}
            response = requests.get(API_URL, params=params)
            
            if response.status_code != 200:
                self.update_status("Erro na API. As credenciais estão corretas?", "red")
                return
            
            data = response.json()
            if "Achievements" not in data or not data["Achievements"]:
                self.update_status("Nenhuma conquista encontrada para este ID.", "red")
                return

            achievements = data["Achievements"]

            folder_name = os.path.join(target_dir, f"badges_{game_id}")
            os.makedirs(folder_name, exist_ok=True)

            total = len(achievements)
            count = 0

            for ach_id, ach_data in achievements.items():
                badge_name = ach_data.get("BadgeName")
                if badge_name:
                    img_url = BADGE_URL.format(badge_name)
                    img_res = requests.get(img_url)
                    
                    if img_res.status_code == 200:
                        save_path = os.path.join(folder_name, f"{badge_name}.png")
                        with open(save_path, "wb") as f:
                            f.write(img_res.content)
                
                count += 1
                self.update_status(f"A transferir badges: {count}/{total}...", "white")

            self.update_status(f"Concluído! Guardado em:\n{folder_name}", "green")

        except Exception as e:
            self.update_status(f"Erro inesperado: {str(e)}", "red")
        finally:
            self.after(0, lambda: self.btn_download.configure(state="normal"))

    def update_status(self, text, color):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

if __name__ == "__main__":
    app = BadgeDownloaderApp()
    app.mainloop()