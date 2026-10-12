import sqlite3
from pathlib import Path

class Store:
    def __init__(self,path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS configs(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL COLLATE NOCASE UNIQUE,filename TEXT NOT NULL COLLATE NOCASE UNIQUE,file_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
    def get(self,i):
        r=self.db.execute('SELECT * FROM configs WHERE id=?',(i,)).fetchone()
        return dict(r) if r else None
    def add(self,filename,file_id):
        if not filename or not filename.lower().endswith('.hc'): raise ValueError('File harus .hc')
        name=filename[:-3].strip()
        if not name or len(name)>100: raise ValueError('Nama harus 1-100 karakter')
        try:
            with self.db:
                c=self.db.execute('INSERT INTO configs(name,filename,file_id) VALUES(?,?,?)',(name,filename,file_id))
            return c.lastrowid
        except sqlite3.IntegrityError: raise ValueError('Nama config sudah ada') from None
    def all(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM configs ORDER BY name COLLATE NOCASE')]
    def duplicate(self,filename):
        r=self.db.execute('SELECT * FROM configs WHERE filename=? COLLATE NOCASE OR name=? COLLATE NOCASE',(filename,filename[:-3].strip())).fetchone()
        return dict(r) if r else None
    def rename(self,i,name):
        name=name.strip()
        if not name or len(name)>100: raise ValueError('Nama harus 1-100 karakter')
        try:
            with self.db: self.db.execute('UPDATE configs SET name=? WHERE id=?',(name,i))
        except sqlite3.IntegrityError: raise ValueError('Nama sudah dipakai') from None
    def replace(self,i,file_id):
        with self.db: self.db.execute('UPDATE configs SET file_id=? WHERE id=?',(file_id,i))
    def delete(self,i):
        with self.db: self.db.execute('DELETE FROM configs WHERE id=?',(i,))
    def clear(self):
        with self.db: self.db.execute('DELETE FROM configs')
    def register(self,i):
        with self.db: self.db.execute('INSERT INTO users(id) VALUES(?) ON CONFLICT(id) DO UPDATE SET active=1',(i,))
    def deactivate(self,i):
        with self.db: self.db.execute('UPDATE users SET active=0 WHERE id=?',(i,))
    def users(self):
        return [r[0] for r in self.db.execute('SELECT id FROM users WHERE active=1')]
    def setting(self,key,value=None):
        if value is not None:
            with self.db: self.db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
        r=self.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r[0] if r else ''
