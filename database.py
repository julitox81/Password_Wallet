"""
Módulo de Persistência e Criptografia - Local Shield Wallet.
Autor: Júlio Carnicelli
"""
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

    def _initialize_db(self):
        """Cria as tabelas necessárias para o funcionamento do cofre."""
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS passwords 
                            (id INTEGER PRIMARY KEY, service TEXT, username TEXT, password TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS config 
                            (key TEXT PRIMARY KEY, value TEXT)''')
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
        """Gera a chave de criptografia Fernet baseada na senha mestra."""
        salt = b'static_salt_for_local_wallet' 
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return Fernet(key)

    def add_entry(self, cipher, service, user, pwd):
        """Criptografa e armazena uma nova credencial no banco."""
        enc_pwd = cipher.encrypt(pwd.encode()).decode()
        self.cursor.execute("INSERT INTO passwords (service, username, password) VALUES (?, ?, ?)",
                            (service, user, enc_pwd))
        self.conn.commit()

    def get_entries(self, cipher):
        """Retorna todas as entradas descriptografadas."""
        self.cursor.execute("SELECT * FROM passwords")
        rows = self.cursor.fetchall()
        decrypted_entries = []
        for row in rows:
            try:
                dec_pwd = cipher.decrypt(row[3].encode()).decode()
                decrypted_entries.append((row[0], row[1], row[2], dec_pwd))
            except Exception as e:
                print(f"Erro ao descriptografar registro {row[0]}: {e}")
                continue
        return decrypted_entries

    def delete_entry(self, entry_id):
        self.cursor.execute("DELETE FROM passwords WHERE id=?", (entry_id,))
        self.conn.commit()

    def export_to_csv(self, cipher, filepath):
        """Exporta os dados em formato legível (CSV)."""
        entries = self.get_entries(cipher)
        if not entries: return False
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Servico", "Usuario", "Senha"])
                for item in entries:
                    writer.writerow([item[1], item[2], item[3]])
            return True
        except IOError:
            return False

    def backup_database(self, destination_folder):
        """Cria uma cópia física do banco de dados com timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(destination_folder, f"vault_backup_{timestamp}.db")
        shutil.copy2("vault.db", dest_path)
        return dest_path