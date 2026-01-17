"""
Local Shield Wallet - Interface Gráfica de Usuário.
Autor: Júlio Carnicelli
"""
import customtkinter as ctk
import secrets
import string
import csv
import tkinter.filedialog as fd
from database import PasswordDB
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WalletApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local Shield Wallet")
        self.geometry("900x700")
        
        self.db = PasswordDB()
        self.cipher = None
        self.timeout_minutes = 5
        self.last_interaction_id = None
        
        self.show_login()

    def reset_timer(self, event=None):
        """Reinicia o cronômetro de inatividade para segurança."""
        if self.last_interaction_id:
            self.after_cancel(self.last_interaction_id)
        if self.cipher:
            self.last_interaction_id = self.after(self.timeout_minutes * 60000, self.lock_wallet)

    def lock_wallet(self):
        """Limpa a sessão e retorna à tela de login por inatividade."""
        self.cipher = None
        for widget in self.winfo_children():
            widget.destroy()
        self.show_login()
        messagebox.showinfo("Segurança", "Sessão encerrada por inatividade.")

    def show_login(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.45, relheight=0.5)
        
        ctk.CTkLabel(self.login_frame, text="🔒 Local Shield", font=("Roboto", 28, "bold")).pack(pady=(40, 20))
        
        self.master_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Senha Mestra", show="*", height=45)
        self.master_entry.pack(pady=10, padx=40, fill="x")
        self.master_entry.bind("<Return>", lambda e: self.unlock())
        self.master_entry.focus_set()
        
        ctk.CTkButton(self.login_frame, text="Acessar Vault", height=45, command=self.unlock).pack(pady=30, padx=40, fill="x")

    def unlock(self):
        pwd = self.master_entry.get()
        if self.db.verify_master(pwd):
            self.cipher = self.db.derive_key(pwd)
            self.login_frame.destroy()
            
            # Ativa monitoramento global de inatividade
            self.bind_all("<Any-KeyPress>", self.reset_timer)
            self.bind_all("<Any-ButtonPress>", self.reset_timer)
            self.reset_timer()
            
            self.show_dashboard()
        else:
            messagebox.showerror("Erro", "Senha Mestra incorreta!")

    def show_dashboard(self):
        self.dash_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dash_frame.pack(fill="both", expand=True, padx=30, pady=30)

        header = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 25))
        
        self.search_entry = ctk.CTkEntry(header, placeholder_text="🔍 Buscar nos seus registros...", height=45)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        ctk.CTkButton(header, text="⚙️", width=50, height=45, fg_color="gray25", command=self.show_settings).pack(side="right", padx=5)
        ctk.CTkButton(header, text="+ Adicionar", width=140, height=45, command=self.add_popup).pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(self.dash_frame, fg_color="#1a1a1a", corner_radius=15)
        self.scroll_frame.pack(fill="both", expand=True)
        self.refresh_list()

    def refresh_list(self):
        query = self.search_entry.get().lower()
        entries = self.db.get_entries(self.cipher) or []
        
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        
        filtered = [i for i in entries if query in i[1].lower() or query in i[2].lower()]
        
        for item in filtered:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", height=75, corner_radius=12)
            row.pack(fill="x", pady=8, padx=15)
            row.pack_propagate(False)

            # Texto: Serviço e Usuário
            txt_container = ctk.CTkFrame(row, fg_color="transparent")
            txt_container.pack(side="left", padx=20, fill="y")
            ctk.CTkLabel(txt_container, text=item[1].upper(), font=("Roboto", 13, "bold"), anchor="w").pack(side="top", pady=(12,0), fill="x")
            ctk.CTkLabel(txt_container, text=item[2], font=("Roboto", 11), text_color="gray", anchor="w").pack(side="top", fill="x")
            
            # Senha com Máscara Fixa (8 caracteres sempre)
            p_container = ctk.CTkFrame(row, fg_color="transparent")
            p_container.pack(side="left", expand=True)
            
            p_field = ctk.CTkEntry(p_container, width=150, border_width=0, fg_color="transparent", show="*", justify="center")
            p_field.insert(0, "********")
            p_field.configure(state="readonly")
            p_field.pack()

            # Ações
            btn_container = ctk.CTkFrame(row, fg_color="transparent")
            btn_container.pack(side="right", padx=15)

            ctk.CTkButton(btn_container, text="🗑️", width=40, height=35, fg_color="#d32f2f", command=lambda i=item[0]: self.delete_entry(i)).pack(side="right", padx=5)
            ctk.CTkButton(btn_container, text="📋", width=40, height=35, command=lambda p=item[3]: self.copy_to_clipboard(p)).pack(side="right", padx=5)
            
            def toggle_visibility(f=p_field, real_pwd=item[3]):
                if f.cget("show") == "*":
                    f.configure(state="normal")
                    f.delete(0, 'end')
                    f.insert(0, real_pwd)
                    f.configure(show="", state="readonly")
                else:
                    f.configure(state="normal")
                    f.delete(0, 'end')
                    f.insert(0, "********")
                    f.configure(show="*", state="readonly")
            
            ctk.CTkButton(btn_container, text="👁️", width=40, height=35, fg_color="gray30", command=toggle_visibility).pack(side="right", padx=5)

    def show_settings(self):
        win = ctk.CTkToplevel(self)
        win.geometry("450x400")
        win.title("Configurações")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text="Gestão de Dados", font=("Roboto", 20, "bold")).pack(pady=25)
        
        def run_bkp():
            path = fd.askdirectory(title="Local de Backup")
            if path: messagebox.showinfo("Backup", f"Arquivo salvo: {self.db.backup_database(path)}")
        
        ctk.CTkButton(win, text="☁️ Backup da Base", height=40, command=run_bkp).pack(pady=10, padx=40, fill="x")
        
        def run_exp():
            path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if path and self.db.export_to_csv(self.cipher, path): messagebox.showinfo("OK", "Dados exportados!")
            
        ctk.CTkButton(win, text="📤 Exportar CSV", height=40, fg_color="gray30", command=run_exp).pack(pady=10, padx=40, fill="x")

    def add_popup(self):
        pop = ctk.CTkToplevel(self)
        pop.geometry("400x550")
        pop.attributes("-topmost", True)
        
        ctk.CTkLabel(pop, text="Nova Credencial", font=("Roboto", 18, "bold")).pack(pady=20)
        s_en = ctk.CTkEntry(pop, placeholder_text="Serviço", height=40)
        s_en.pack(pady=10, padx=30, fill="x")
        u_en = ctk.CTkEntry(pop, placeholder_text="Usuário", height=40)
        u_en.pack(pady=10, padx=30, fill="x")
        p_en = ctk.CTkEntry(pop, placeholder_text="Senha", height=40)
        p_en.pack(pady=10, padx=30, fill="x")
        
        def generate():
            pwd = ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(20))
            p_en.delete(0, 'end')
            p_en.insert(0, pwd)
            
        ctk.CTkButton(pop, text="Gerar Senha Forte", fg_color="gray40", command=generate).pack(pady=10)
        
        def save():
            if s_en.get() and p_en.get():
                self.db.add_entry(self.cipher, s_en.get(), u_en.get(), p_en.get())
                pop.destroy()
                self.refresh_list()
                
        ctk.CTkButton(pop, text="Salvar", height=45, fg_color="#2e7d32", command=save).pack(pady=20, padx=30, fill="x")

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.title("✅ SENHA COPIADA!")
        self.after(2000, lambda: self.title("Local Shield Wallet"))

    def delete_entry(self, entry_id):
        if messagebox.askyesno("Confirmar", "Deseja excluir permanentemente?"):
            self.db.delete_entry(entry_id)
            self.refresh_list()

if __name__ == "__main__":
    app = WalletApp()
    app.mainloop()