# 📦 Config Free Bot

Bot Telegram untuk distribusi config `.hc` gratis. SQLite, owner-only, private chat, UI premium dengan emoji.

## ✨ Fitur

- 📥 Download config `.hc` gratis
- ➕ Upload config (single & batch)
- ✏️ Rename config
- 🗑️ Delete config (single & semua)
- 📢 Broadcast ke semua user
- 👤 Atur kontak admin (WhatsApp & Telegram)
- 🎨 UI premium: emoji, HTML formatting, edit-in-place (pesan di-edit, bukan numpuk)
- 🔄 Supervisor: auto-restart kalau crash

## 🚀 Instalasi

### Metode 1: Interactive (direkomendasikan)

```bash
curl -fsSL https://raw.githubusercontent.com/akunkhususjualanssh-create/config-free-bot/main/install.sh | bash
```

Atau download dulu:

```bash
wget https://raw.githubusercontent.com/akunkhususjualanssh-create/config-free-bot/main/install.sh
bash install.sh
```

Installer akan minta:
1. **Bot Token** — dari @BotFather
2. **Owner ID** — Telegram ID lu (cek di @userinfobot)

### Metode 2: Quick Install (langsung pass token & owner ID)

```bash
bash install.sh --token 123456789:ABCdefGHIjklMNOpqrSTUvwx --owner 7761880504
```

## 📋 Persyaratan

- VPS root access (Debian/Ubuntu)
- Python 3.10+
- Bot token dari @BotFather

## 🛠️ Commands

```bash
# Start bot
/opt/config-free/.venv/bin/supervisord -c /opt/config-free/supervisord.conf

# Status
/opt/config-free/.venv/bin/supervisorctl -c /opt/config-free/supervisord.conf status

# Restart
/opt/config-free/.venv/bin/supervisorctl -c /opt/config-free/supervisord.conf restart config-free

# Log
tail -f /opt/config-free/logs/bot.log
```

## 📁 Struktur

```
/opt/config-free/
├── bot.py              # Main bot
├── store.py            # SQLite database layer
├── configure_bot.py    # Set bot name, description, commands
├── send_ready.py       # Send ready notification to owner
├── requirements.txt    # Python dependencies
├── supervisord.conf    # Supervisor config
├── .env                # Bot token & owner ID (chmod 600)
├── data/bot.db         # SQLite database
├── logs/               # Log files
└── .venv/              # Python virtual environment
```

## 🔒 Keamanan

- Token disimpan di `.env` (chmod 600)
- `.env` di `.gitignore` — tidak ter-upload ke GitHub
- File config disimpan sebagai `file_id` Telegram

## 📝 Pemakaian Bot

- `/start` — Buka menu utama
- `/cancel` — Batalkan input
- **Config Free** — Pilih & download config
- **List Config** — Lihat daftar semua config
- **Hubungi Admin** — Kontak admin (WhatsApp/Telegram)
- **Menu Admin** (owner only):
  - Add Config / Batch Upload
  - Delete / Hapus Semua
  - Kelola (Rename)
  - Broadcast
  - Atur Kontak
