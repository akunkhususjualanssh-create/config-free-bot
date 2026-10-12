#!/bin/bash
# ============================================================
#  Config Free Bot - Installer
#  Method 1: bash install.sh
#    → Interactive: prompt bot token & owner ID
#  Method 2: bash install.sh --token TOKEN --owner OWNER_ID
#    → Quick: langsung pass token & owner ID
# ============================================================
set -e

INSTALL_DIR="/opt/config-free"
SERVICE_USER="configfree"
REPO_URL="https://raw.githubusercontent.com/akunkhususjualanssh-create/config-free-bot/main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮"
    echo "   CONFIG FREE BOT INSTALLER"
    echo "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    echo -e "${NC}"
}

print_ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
print_info() { echo -e "${CYAN}[ℹ]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_err()  { echo -e "${RED}[✗]${NC} $1"; }

# Parse arguments
BOT_TOKEN=""
ADMIN_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --token)
            BOT_TOKEN="$2"; shift 2 ;;
        --owner)
            ADMIN_ID="$2"; shift 2 ;;
        --help|-h)
            echo "Usage:"
            echo "  bash install.sh                          # Interactive mode"
            echo "  bash install.sh --token TOKEN --owner ID # Quick mode"
            echo ""
            echo "Options:"
            echo "  --token   Bot token dari @BotFather"
            echo "  --owner   Owner/Admin Telegram ID"
            exit 0 ;;
        *)
            print_err "Unknown option: $1"; exit 1 ;;
    esac
done

print_banner

# Root check
if [[ $EUID -ne 0 ]]; then
    print_err "Run as root!"
    exit 1
fi

# Interactive prompt if not provided via args
if [[ -z "$BOT_TOKEN" ]]; then
    echo -e "${YELLOW}━━━ METODE 1: INTERACTIVE ━━━${NC}"
    echo ""
    while true; do
        read -p "🔑 Masukkan Bot Token (dari @BotFather): " BOT_TOKEN
        if [[ -z "$BOT_TOKEN" ]]; then
            print_err "Bot token tidak boleh kosong!"
        elif [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
            print_ok "Token diterima"
            break
        else
            print_err "Format token tidak valid! Contoh: 123456789:ABCdef..."
        fi
    done
    echo ""
    while true; do
        read -p "👤 Masukkan Owner ID (Telegram ID Anda): " ADMIN_ID
        if [[ -z "$ADMIN_ID" ]]; then
            print_err "Owner ID tidak boleh kosong!"
        elif [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
            print_ok "Owner ID diterima"
            break
        else
            print_err "Owner ID harus angka! Cek di @userinfobot"
        fi
    done
else
    if [[ -z "$ADMIN_ID" ]]; then
        print_err "--token diberikan tapi --owner kosong!"
        echo "Usage: bash install.sh --token TOKEN --owner ID"
        exit 1
    fi
    echo -e "${YELLOW}━━━ METODE 2: QUICK INSTALL ━━━${NC}"
    print_ok "Bot Token: ${BOT_TOKEN:0:12}..."
    print_ok "Owner ID: $ADMIN_ID"
fi

echo ""
print_info "Memulai instalasi..."

# Step 1: System packages
print_info "1/8 Installing system packages..."
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq python3 python3-venv python3-pip curl >/dev/null 2>&1
print_ok "System packages ready"

# Step 2: Create service user
print_info "2/8 Setting up service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    print_ok "User '$SERVICE_USER' created"
else
    print_ok "User '$SERVICE_USER' already exists"
fi

# Step 3: Create directories
print_info "3/8 Creating directories..."
mkdir -p "$INSTALL_DIR"/{data,logs,run}
print_ok "Directories created: $INSTALL_DIR"

# Step 4: Download files
print_info "4/8 Downloading bot files..."
FILES=("bot.py" "store.py" "configure_bot.py" "send_ready.py" "requirements.txt" "supervisord.conf")
for f in "${FILES[@]}"; do
    curl -sfL "$REPO_URL/$f" -o "$INSTALL_DIR/$f"
    if [[ $? -ne 0 ]]; then
        print_err "Failed to download: $f"
        exit 1
    fi
done
print_ok "Bot files downloaded (${#FILES[@]} files)"

# Step 5: Python venv + deps
print_info "5/8 Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
"$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt" 2>&1 | tail -1
print_ok "Python venv + dependencies installed"

# Step 6: Write .env
print_info "6/8 Writing configuration..."
cat > "$INSTALL_DIR/.env" << EOF
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
DB_PATH=$INSTALL_DIR/data/bot.db
EOF
chmod 600 "$INSTALL_DIR/.env"
print_ok ".env written (secured)"

# Step 7: Fix permissions
print_info "7/8 Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod -R go-rwx "$INSTALL_DIR/.env"
print_ok "Permissions set"

# Step 8: Configure bot (set name, description, commands)
print_info "8/8 Configuring Telegram bot..."
cd "$INSTALL_DIR"
"$INSTALL_DIR/.venv/bin/python" configure_bot.py 2>&1 || {
    print_warn "Bot configure skipped (mungkin token belum valid)"
}
print_ok "Bot configured"

# Start bot via supervisor
print_info "Starting bot..."
cd "$INSTALL_DIR"
"$INSTALL_DIR/.venv/bin/supervisord" -c "$INSTALL_DIR/supervisord.conf" 2>/dev/null || true
sleep 3

# Send ready message
print_info "Sending ready notification..."
"$INSTALL_DIR/.venv/bin/python" send_ready.py 2>&1 || {
    print_warn "Silakan /start bot di Telegram dulu, lalu restart:"
    echo "  $INSTALL_DIR/.venv/bin/supervisorctl -c $INSTALL_DIR/supervisord.conf restart config-free"
}

# Verify
STATUS=$("$INSTALL_DIR/.venv/bin/supervisorctl" -c "$INSTALL_DIR/supervisord.conf" status config-free 2>/dev/null | awk '{print $2}')
if [[ "$STATUS" == "RUNNING" ]]; then
    print_ok "Bot is RUNNING"
else
    print_warn "Bot status: $STATUS — cek log: $INSTALL_DIR/logs/bot.log"
fi

echo ""
echo -e "${GREEN}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮${NC}"
echo -e "${GREEN}   ✅ INSTALASI SELESAI!${NC}"
echo -e "${GREEN}╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯${NC}"
echo ""
echo -e "  ${CYAN}Bot dir:${NC}    $INSTALL_DIR"
echo -e "  ${CYAN}Database:${NC}    $INSTALL_DIR/data/bot.db"
echo -e "  ${CYAN}Logs:${NC}       $INSTALL_DIR/logs/bot.log"
echo ""
echo -e "  ${YELLOW}Commands:${NC}"
echo "  Start:   $INSTALL_DIR/.venv/bin/supervisord -c $INSTALL_DIR/supervisord.conf"
echo "  Status:  $INSTALL_DIR/.venv/bin/supervisorctl -c $INSTALL_DIR/supervisord.conf status"
echo "  Restart: $INSTALL_DIR/.venv/bin/supervisorctl -c $INSTALL_DIR/supervisord.conf restart config-free"
echo "  Logs:    tail -f $INSTALL_DIR/logs/bot.log"
echo ""
echo -e "  ${GREEN}Buka Telegram dan /start bot lu! 🤖${NC}"
