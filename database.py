import sqlite3
import base64
import hashlib
import os
import shutil
import csv
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

class PasswordDB:
    def __init__(self, db_path="vault.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._initialize_db()
        self._migrate()

    def _initialize_db(self):
        """Cria as tabelas necessárias para o funcionamento do cofre."""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS passwords 
                            (id INTEGER PRIMARY KEY, service TEXT, url TEXT, username TEXT, password TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS config 
                            (key TEXT PRIMARY KEY, value TEXT)''')
        self.conn.commit()

    def _migrate(self):
        """Adiciona a coluna URL se ela não existir (Retrocompatibilidade)."""
        self.cursor.execute("PRAGMA table_info(passwords)")
        columns = [col[1] for col in self.cursor.fetchall()]
        if 'url' not in columns:
            self.cursor.execute("ALTER TABLE passwords ADD COLUMN url TEXT DEFAULT ''")
            self.conn.commit()

    def verify_master(self, master_password):
        """Valida a senha mestra ou registra uma nova no primeiro acesso."""
        self.cursor.execute("SELECT value FROM config WHERE key='master_hash'")
        result = self.cursor.fetchone()
        salt = "secure_random_salt_123"
        hashed = hashlib.sha256((master_password + salt).encode()).hexdigest()
        if not result:
            self.cursor.execute("INSERT INTO config (key, value) VALUES ('master_hash', ?)", (hashed,))
            self.conn.commit()
            return True
        return hashed == result[0]

    def derive_key(self, master_password):
        """Deriva uma chave segura para criptografia AES."""
        salt = b'static_salt_for_local_wallet' 
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return Fernet(key)

    def add_entry(self, cipher, service, url, user, pwd):
        enc_pwd = cipher.encrypt(pwd.encode()).decode()
        self.cursor.execute("INSERT INTO passwords (service, url, username, password) VALUES (?, ?, ?, ?)",
                            (service, url, user, enc_pwd))
        self.conn.commit()

    def update_entry(self, cipher, entry_id, service, url, user, pwd):
        enc_pwd = cipher.encrypt(pwd.encode()).decode()
        self.cursor.execute("UPDATE passwords SET service=?, url=?, username=?, password=? WHERE id=?",
                            (service, url, user, enc_pwd, entry_id))
        self.conn.commit()

    def get_entries(self, cipher):
        self.cursor.execute("SELECT id, service, url, username, password FROM passwords")
        rows = self.cursor.fetchall()
        decrypted_entries = []
        for row in rows:
            try:
                dec_pwd = cipher.decrypt(row[4].encode()).decode()
                decrypted_entries.append((row[0], row[1], row[2], row[3], dec_pwd))
            except:
                continue
        return decrypted_entries

    def delete_entry(self, entry_id):
        self.cursor.execute("DELETE FROM passwords WHERE id=?", (entry_id,))
        self.conn.commit()

    # --- FUNÇÕES DE GESTÃO DE DADOS ---
    def export_to_csv(self, cipher, filepath):
        entries = self.get_entries(cipher)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Servico", "URL", "Usuario", "Senha"])
                for item in entries:
                    writer.writerow([item[1], item[2], item[3], item[4]])
            return True
        except: return False

    def import_from_csv(self, cipher, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f: # 'utf-8-sig' lida com arquivos do Excel
                # Usamos o DictReader mas limpamos possíveis espaços em branco nos nomes das colunas
                reader = csv.DictReader(f)
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
                
                for row in reader:
                    # Garantimos que os campos existam, mesmo que vazios ou com espaços
                    service = row.get('Servico', '').strip()
                    url = row.get('URL', '').strip()
                    user = row.get('Usuario', '').strip()
                    pwd = row.get('Senha', '').strip()
                    
                    if service and pwd: # Só importa se tiver pelo menos o nome e a senha
                        self.add_entry(cipher, service, url, user, pwd)
            return True
        except Exception as e:
            print(f"Erro detalhado na importação: {e}")
            return False

    def backup_database(self, destination_folder):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(destination_folder, f"vault_backup_{timestamp}.db")
        shutil.copy2("vault.db", dest_path)
        return dest_path