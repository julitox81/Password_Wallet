import customtkinter as ctk
import secrets
import string
import webbrowser
import tkinter.filedialog as fd
from database import PasswordDB
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WalletApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local Shield Wallet")
        self.geometry("950x700")
        self.db = PasswordDB()
        self.cipher = None
        self.timeout_minutes = 5
        self.last_interaction_id = None
        self.show_login()

    def reset_timer(self, event=None):
        if self.last_interaction_id: self.after_cancel(self.last_interaction_id)
        if self.cipher: self.last_interaction_id = self.after(self.timeout_minutes * 60000, self.lock_wallet)

    def lock_wallet(self):
        self.cipher = None
        for widget in self.winfo_children(): widget.destroy()
        self.show_login()
        messagebox.showinfo("Segurança", "Sessão encerrada por inatividade.")

    def show_login(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.4, relheight=0.45)
        ctk.CTkLabel(self.login_frame, text="🔒 Local Shield", font=("Roboto", 24, "bold")).pack(pady=20)
        self.master_entry = ctk.CTkEntry(self.login_frame, placeholder_text="Senha Mestra", show="*", height=40)
        self.master_entry.pack(pady=10, padx=30, fill="x")
        self.master_entry.bind("<Return>", lambda e: self.unlock())
        ctk.CTkButton(self.login_frame, text="Desbloquear", height=40, command=self.unlock).pack(pady=20, padx=30, fill="x")

    def unlock(self):
        pwd = self.master_entry.get()
        if self.db.verify_master(pwd):
            self.cipher = self.db.derive_key(pwd)
            self.login_frame.destroy()
            self.bind_all("<Any-KeyPress>", self.reset_timer)
            self.bind_all("<Any-ButtonPress>", self.reset_timer)
            self.reset_timer()
            self.show_dashboard()
        else: messagebox.showerror("Erro", "Senha incorreta!")

    def show_dashboard(self):
        self.dash_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dash_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header = ctk.CTkFrame(self.dash_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        
        self.search_entry = ctk.CTkEntry(header, placeholder_text="🔍 Pesquisar serviço...", height=40)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())
        
        ctk.CTkButton(header, text="+ Adicionar", width=120, height=40, command=self.add_popup).pack(side="left", padx=5)
        ctk.CTkButton(header, text="⚙️", width=40, height=40, fg_color="gray30", command=self.show_settings).pack(side="left")

        self.scroll_frame = ctk.CTkScrollableFrame(self.dash_frame, fg_color="#1a1a1a", corner_radius=10)
        self.scroll_frame.pack(fill="both", expand=True)
        self.refresh_list()

    def show_settings(self):
        set_pop = ctk.CTkToplevel(self)
        set_pop.title("Configurações")
        set_pop.geometry("300x400")
        set_pop.attributes("-topmost", True)
        
        ctk.CTkLabel(set_pop, text="Opções de Dados", font=("Roboto", 16, "bold")).pack(pady=20)
        
        # Os botões já estão vinculados às funções abaixo
        ctk.CTkButton(set_pop, text="Importar CSV", command=self.import_data).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(set_pop, text="Exportar CSV", command=self.export_data).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(set_pop, text="Backup Banco (.db)", command=self.backup_db).pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(set_pop, text="v2.5 Local Storage", font=("Roboto", 10), text_color="gray").pack(side="bottom", pady=10)

    # NOVO IMPORTADOR AJUSTADO
    def import_data(self):
        path = fd.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            if self.db.import_from_csv(self.cipher, path):
                messagebox.showinfo("Sucesso", "Dados importados com sucesso!")
                self.refresh_list()
            else:
                messagebox.showerror("Erro de Formatação", 
                    "Não foi possível importar. Verifique se o CSV possui os cabeçalhos:\nServico, URL, Usuario, Senha")

    def export_data(self):
        path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            if self.db.export_to_csv(self.cipher, path):
                messagebox.showinfo("Sucesso", "Dados exportados com segurança!")

    def backup_db(self):
        folder = fd.askdirectory()
        if folder:
            path = self.db.backup_database(folder)
            messagebox.showinfo("Backup", f"Backup criado em:\n{path}")

    def refresh_list(self):
        query = self.search_entry.get().lower()
        for w in self.scroll_frame.winfo_children(): w.destroy()
        entries = self.db.get_entries(self.cipher) or []
        filtered = [e for e in entries if query in e[1].lower()]
        
        for item in filtered:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", height=60, corner_radius=8)
            row.pack(fill="x", pady=4, padx=5)
            row.pack_propagate(False)

            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", padx=15)
            ctk.CTkLabel(info_frame, text=item[1].upper(), font=("Roboto", 13, "bold"), anchor="w").pack(anchor="w")
            
            if item[2]:
                lbl_url = ctk.CTkLabel(info_frame, text="Acessar Site 🔗", font=("Roboto", 10), text_color="#3a7ebf", cursor="hand2")
                lbl_url.pack(anchor="w")
                lbl_url.bind("<Button-1>", lambda e, url=item[2]: webbrowser.open(url if url.startswith("http") else f"https://{url}"))

            p_field = ctk.CTkEntry(row, width=100, border_width=0, fg_color="transparent", show="*", justify="center")
            p_field.insert(0, "********")
            p_field.configure(state="readonly")
            p_field.pack(side="left", expand=True)

            btn_container = ctk.CTkFrame(row, fg_color="transparent")
            btn_container.pack(side="right", padx=10)

            def toggle_view(f=p_field, p=item[4]):
                if f.cget("show") == "*":
                    f.configure(state="normal"); f.delete(0, 'end'); f.insert(0, p); f.configure(show="", state="readonly")
                else:
                    f.configure(state="normal"); f.delete(0, 'end'); f.insert(0, "********"); f.configure(show="*", state="readonly")

            ctk.CTkButton(btn_container, text="Ver", width=45, height=30, fg_color="gray30", command=toggle_view).pack(side="left", padx=2)
            ctk.CTkButton(btn_container, text="Copiar", width=55, height=30, fg_color="#1f538d", command=lambda p=item[4]: self.copy_to_clipboard(p)).pack(side="left", padx=2)
            ctk.CTkButton(btn_container, text="Editar", width=55, height=30, fg_color="#e67e22", command=lambda d=item: self.add_popup(edit_data=d)).pack(side="left", padx=2)
            ctk.CTkButton(btn_container, text="Excluir", width=55, height=30, fg_color="#d32f2f", command=lambda i=item[0]: self.delete_entry(i)).pack(side="left", padx=2)

    def add_popup(self, edit_data=None):
        pop = ctk.CTkToplevel(self)
        pop.geometry("400x550")
        pop.title("Editar" if edit_data else "Novo Registro")
        pop.attributes("-topmost", True)
        ctk.CTkLabel(pop, text="Dados da Credencial", font=("Roboto", 18, "bold")).pack(pady=20)
        
        s_en = ctk.CTkEntry(pop, placeholder_text="Serviço", height=40); s_en.pack(pady=8, padx=30, fill="x")
        url_en = ctk.CTkEntry(pop, placeholder_text="URL (ex: google.com)", height=40); url_en.pack(pady=8, padx=30, fill="x")
        u_en = ctk.CTkEntry(pop, placeholder_text="Usuário", height=40); u_en.pack(pady=8, padx=30, fill="x")
        p_en = ctk.CTkEntry(pop, placeholder_text="Senha", height=40); p_en.pack(pady=8, padx=30, fill="x")

        if edit_data:
            s_en.insert(0, edit_data[1]); url_en.insert(0, edit_data[2]); u_en.insert(0, edit_data[3]); p_en.insert(0, edit_data[4])

        def gen():
            p_en.delete(0, 'end'); p_en.insert(0, ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(16)))
        
        ctk.CTkButton(pop, text="Gerar Senha", fg_color="gray40", command=gen).pack(pady=10)
        
        def save():
            if s_en.get() and p_en.get():
                if edit_data: self.db.update_entry(self.cipher, edit_data[0], s_en.get(), url_en.get(), u_en.get(), p_en.get())
                else: self.db.add_entry(self.cipher, s_en.get(), url_en.get(), u_en.get(), p_en.get())
                pop.destroy(); self.refresh_list()

        ctk.CTkButton(pop, text="Salvar", height=45, fg_color="#2e7d32", command=save).pack(pady=20, padx=30, fill="x")

    def copy_to_clipboard(self, text):
        self.clipboard_clear(); self.clipboard_append(text)
        self.title("✅ COPIADO!"); self.after(1500, lambda: self.title("Local Shield Wallet"))

    def delete_entry(self, entry_id):
        if messagebox.askyesno("Excluir", "Apagar permanentemente?"):
            self.db.delete_entry(entry_id); self.refresh_list()

if __name__ == "__main__":
    app = WalletApp()
    app.mainloop()