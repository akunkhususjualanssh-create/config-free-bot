import asyncio, logging, os
from html import escape
from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Markup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest
from dotenv import load_dotenv
from store import Store

log = logging.getLogger(__name__)

def keyboard(rows):
    return Markup([[Button(label, callback_data=data) for label, data in row] for row in rows])

def main_menu():
    return keyboard([
        [('📥 Config Free', 'page:get:0'), ('📋 List Config', 'list')],
        [('👤 Hubungi Admin', 'contact')],
        [('⚙️ Menu Admin', 'admin')]
    ])

def admin_menu():
    return keyboard([
        [('➕ Add Config', 'a:add'), ('📦 Batch Upload', 'a:batch')],
        [('🗑️ Hapus Config', 'page:del:0'), ('💣 Hapus Semua', 'a:clear')],
        [('✏️ Kelola Config', 'page:rename:0'), ('📢 Broadcast', 'a:broadcast')],
        [('📞 Atur Kontak', 'a:contact')],
        [('🏠 Menu Utama', 'home')]
    ])

def owner(u, c): return u.effective_user.id == c.bot_data['owner']
def private(u): return u.effective_chat and u.effective_chat.type == 'private'
def store(c): return c.bot_data['store']
def esc(s): return escape(str(s))

WELCOME = (
    "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
    "   📦 <b>CONFIG FREE</b> 📦\n"
    "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    "✨ Selamat datang!\n"
    "Silakan pilih menu di bawah 👇"
)

ADMIN_HDR = (
    "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
    "   ⚙️ <b>MENU ADMIN</b> ⚙️\n"
    "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    "Pilih aksi di bawah 👇"
)

async def edit_msg(q, c, text, reply_markup=None):
    """Edit pesan di tempat. Kalau gagal, hapus pesan lama + kirim baru."""
    try:
        await q.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except BadRequest as e:
        msg = str(e).lower()
        if 'not modified' in msg:
            return  # konten sama, gak perlu apa-apa
        # Edit gagal — hapus pesan lama, kirim pesan baru
        msg_obj = q.message
        chat = msg_obj.chat
        try:
            await msg_obj.delete()
        except Exception:
            pass
        new_msg = await chat.send_message(text, reply_markup=reply_markup, parse_mode='HTML')
        c.user_data['menu_msg'] = (new_msg.chat_id, new_msg.message_id)

async def start(u, c):
    if not private(u): return
    store(c).register(u.effective_user.id)
    # Hapus pesan menu lama kalau ada
    old = c.user_data.get('menu_msg')
    c.user_data.clear()
    msg = await u.effective_message.reply_text(WELCOME, reply_markup=main_menu(), parse_mode='HTML')
    c.user_data['menu_msg'] = (msg.chat_id, msg.message_id)
    if old:
        try:
            await c.bot.delete_message(chat_id=old[0], message_id=old[1])
        except Exception:
            pass

async def on_callback(u, c):
    if not private(u): return
    q = u.callback_query; data = q.data or ''
    public = data in ('home', 'list', 'contact') or data.startswith(('get:', 'page:get:'))
    if not public and not owner(u, c):
        await q.answer('⛔ Menu ini khusus admin.', show_alert=True); return
    await q.answer()
    s = store(c); s.register(u.effective_user.id)

    if data == 'home':
        c.user_data.clear()
        return await edit_msg(q, c, WELCOME, main_menu())

    if data == 'admin':
        c.user_data.clear()
        return await edit_msg(q, c, ADMIN_HDR, admin_menu())

    if data == 'a:broadcast':
        if c.bot_data.get('broadcast_running'):
            return await edit_msg(q, c, "⏳ <b>Broadcast sebelumnya masih berjalan…</b>")
        c.user_data.clear(); c.user_data['mode'] = 'broadcast'
        return await edit_msg(q, c,
            "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "   📢 <b>BROADCAST</b> 📢\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "Kirim satu pesan pengumuman (teks/foto/video/dokumen).\n"
            "Akan ditampilkan pratinjau sebelum dikirim.\n\n"
            "Album dikirim sebagai pesan terpisah.\n"
            "/cancel untuk batal.")

    if data == 'bc:send':
        source = c.user_data.pop('broadcast', None)
        if not source or c.bot_data.get('broadcast_running'):
            return await edit_msg(q, c, "⚠️ Konfirmasi kedaluwarsa atau broadcast masih berjalan.")
        c.user_data.clear(); c.bot_data['broadcast_running'] = True
        c.application.create_task(broadcast(c, source))
        return await edit_msg(q, c, "📢 <b>Broadcast dimulai!</b>\nHasil akan dikirim setelah selesai.")

    if data in ('a:add', 'a:batch'):
        c.user_data.clear(); c.user_data['mode'] = 'batch' if data == 'a:batch' else 'add'
        return await edit_msg(q, c,
            "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "   📤 <b>UPLOAD CONFIG</b> 📤\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "Silakan kirim file <code>.hc</code>\n"
            "Nama tombol mengikuti nama file.\n\n"
            "Bisa kirim banyak file dalam mode batch.",
            keyboard([[('✅ Selesai', 'done'), ('↩️ Batal', 'admin')]]))

    if data == 'done':
        c.user_data.clear()
        return await edit_msg(q, c, "✅ <b>Selesai!</b>\nFile yang sudah ditambahkan tersimpan.", admin_menu())

    if data.startswith('page:'):
        try:
            _, action, p = data.split(':'); p = max(0, int(p))
            if action not in ('get', 'del', 'rename'): raise ValueError()
        except ValueError: return
        items = s.all(); p = min(p, max(0, (len(items) - 1) // 10))
        rows = [[(r['name'], f"{action}:{r['id']}")] for r in items[p*10:p*10+10]]
        nav = []
        if p: nav.append(('⬅️', f'page:{action}:{p-1}'))
        if (p+1)*10 < len(items): nav.append(('➡️', f'page:{action}:{p+1}'))
        if nav: rows.append(nav)
        rows.append([('🏠 Beranda' if action == 'get' else '↩️ Admin', 'home' if action == 'get' else 'admin')])
        titles = {'get': '📥 Pilih Config', 'del': '🗑️ Hapus Config', 'rename': '✏️ Kelola Config'}
        if items:
            text = f"<b>{titles[action]}</b>\n\n📊 Total: {len(items)} config\nHalaman {p+1} dari {((len(items)-1)//10)+1}"
            return await edit_msg(q, c, text, keyboard(rows))
        return await edit_msg(q, c, "📭 <b>Belum ada config.</b>")

    if data == 'list':
        names = [r['name'] for r in s.all()]
        if not names:
            return await edit_msg(q, c, "📋 <b>LIST CONFIG</b>\n\nBelum ada config tersimpan.")
        text = "📋 <b>LIST CONFIG</b>\n\n"
        for j, name in enumerate(names, 1):
            text += f"{j}. <code>{esc(name)}</code>\n"
        return await edit_msg(q, c, text)

    if data == 'contact':
        tg = s.setting('tg') or f"tg://user?id={c.bot_data['owner']}"
        rows = [[Button('💬 Telegram', url=tg)]]
        if s.setting('wa'): rows.append([Button('📱 WhatsApp', url='https://wa.me/' + s.setting('wa'))])
        return await edit_msg(q, c,
            "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "   👤 <b>HUBUNGI ADMIN</b> 👤\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "Untuk order config, silakan DM admin 👇",
            Markup(rows))

    if data == 'a:contact':
        return await edit_msg(q, c, "📞 <b>ATUR KONTAK</b>\n\nPilih platform:",
            keyboard([[('📱 WhatsApp', 'a:wa'), ('💬 Telegram', 'a:tg')], [('↩️ Kembali', 'admin')]]))

    if data in ('a:wa', 'a:tg'):
        c.user_data.clear(); c.user_data['mode'] = data[2:]
        return await edit_msg(q, c,
            "📱 Kirim nomor WhatsApp format <code>628…</code> (tanpa +)." if data == 'a:wa'
            else "💬 Kirim username Telegram admin, misalnya <code>@username</code>.\n/cancel untuk batal.")

    if data.startswith(('del:', 'rename:')):
        try: action, i = data.split(':'); i = int(i)
        except ValueError: return
        item = s.get(i)
        if not item: return await edit_msg(q, c, "⚠️ Config sudah dihapus.")
        c.user_data.clear()
        if action == 'rename':
            c.user_data.update(mode='rename', item=i)
            return await edit_msg(q, c, f"✏️ <b>GANTI NAMA</b>\n\nConfig: <code>{esc(item['name'])}</code>\n\nKirim nama baru (maksimal 100 karakter).")
        c.user_data['confirm'] = f'del:{i}'
        return await edit_msg(q, c, f"🗑️ <b>KONFIRMASI HAPUS</b>\n\nConfig: <code>{esc(item['name'])}</code>\n\nYakin ingin menghapus?",
            keyboard([[('✅ Ya, hapus', f'yes:del:{i}'), ('❌ Batal', 'admin')]]))

    if data == 'a:clear':
        c.user_data.clear(); c.user_data['confirm'] = 'clear'
        return await edit_msg(q, c, f"💣 <b>HAPUS SEMUA CONFIG</b>\n\nTotal: {len(s.all())} config\n\n⚠️ <b>Tidak bisa dibatalkan!</b>",
            keyboard([[('✅ Ya, hapus semua', 'yes:clear'), ('❌ Batal', 'admin')]]))

    if data.startswith('yes:'):
        action = data[4:]
        if c.user_data.pop('confirm', None) != action:
            return await edit_msg(q, c, "⚠️ Konfirmasi kedaluwarsa. Pilih menu ulang.")
        if action == 'clear': s.clear()
        elif action.startswith('del:'): s.delete(int(action.split(':')[1]))
        return await edit_msg(q, c, "✅ <b>Config berhasil dihapus!</b>", admin_menu())

    if data.startswith(('replace:', 'skip:')):
        action, token = data.split(':', 1)
        item = c.user_data.get('pending', {}).pop(token, None)
        if not item: return await edit_msg(q, c, "⚠️ Konfirmasi sudah dipakai atau kedaluwarsa.")
        if action == 'replace':
            if not s.get(item['id']): return await edit_msg(q, c, "⚠️ Config sudah dihapus. Upload ulang.")
            s.replace(item['id'], item['file_id'])
        return await edit_msg(q, c, "✅ <b>File diganti!</b>" if action == 'replace' else "⏭️ <b>File duplikat dilewati.</b>")

    if data.startswith('get:'):
        try: item = s.get(int(data.split(':')[1]))
        except ValueError: item = None
        if not item: return await edit_msg(q, c, "⚠️ Config sudah tidak tersedia.")
        # Kirim file langsung — menu tetap utuh, gak diubah
        await c.bot.send_document(chat_id=u.effective_chat.id, document=item['file_id'],
            caption=f"📦 <code>{esc(item['name'])}</code>", parse_mode='HTML')
        return

    await edit_msg(q, c, "❓ Tombol tidak tersedia.\nKetik /start.")


async def on_message(u, c):
    if not private(u): return
    s = store(c); s.register(u.effective_user.id)
    mode = c.user_data.get('mode') if owner(u, c) else None

    if mode == 'broadcast':
        from telegram.error import TelegramError
        try:
            await c.bot.copy_message(chat_id=u.effective_chat.id, from_chat_id=u.effective_chat.id, message_id=u.effective_message.message_id)
        except TelegramError:
            return await u.effective_message.reply_text('❌ Pesan ini tidak bisa disalin. Kirim teks/foto/dokumen lain.', parse_mode='HTML')
        c.user_data['broadcast'] = (u.effective_chat.id, u.effective_message.message_id)
        c.user_data['mode'] = 'broadcast_confirm'
        return await u.effective_message.reply_text(
            f'✨ <b>Pratinjau di atas.</b>\n\nKirim ke {len(s.users())} pengguna?',
            reply_markup=keyboard([[('📢 Kirim Broadcast', 'bc:send'), ('❌ Batal', 'admin')]]),
            parse_mode='HTML')

    if mode in ('wa', 'tg', 'rename'):
        import re
        text = (u.effective_message.text or '').strip()
        if mode == 'wa':
            if not re.fullmatch(r'[1-9][0-9]{7,14}', text):
                return await u.effective_message.reply_text('❌ Nomor tidak valid.\n\nGunakan format <code>628123456789</code> (tanpa +).', parse_mode='HTML')
            s.setting('wa', text)
        elif mode == 'tg':
            text = text.removeprefix('https://t.me/').lstrip('@')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}', text):
                return await u.effective_message.reply_text('❌ Username tidak valid.\n\nContoh: <code>@username</code>', parse_mode='HTML')
            s.setting('tg', 'https://t.me/' + text)
        else:
            if not s.get(c.user_data['item']):
                c.user_data.clear()
                return await u.effective_message.reply_text('⚠️ Config sudah dihapus.', parse_mode='HTML')
            try: s.rename(c.user_data['item'], text)
            except ValueError as e: return await u.effective_message.reply_text(f'❌ {esc(e)}', parse_mode='HTML')
        c.user_data.clear()
        return await u.effective_message.reply_text('✅ <b>Perubahan disimpan!</b>', reply_markup=admin_menu(), parse_mode='HTML')

    if mode in ('add', 'batch'):
        import secrets
        doc = u.effective_message.document
        if not doc or not doc.file_name or not doc.file_name.lower().endswith('.hc'):
            return await u.effective_message.reply_text('❌ Kirim file <code>.hc</code> sebagai dokumen.', parse_mode='HTML')
        duplicate = s.duplicate(doc.file_name)
        if duplicate:
            pending = c.user_data.setdefault('pending', {})
            if len(pending) >= 50:
                return await u.effective_message.reply_text('⚠️ Selesaikan konfirmasi duplikat terlebih dahulu.', parse_mode='HTML')
            token = secrets.token_hex(6)
            pending[token] = {'id': duplicate['id'], 'file_id': doc.file_id}
            return await u.effective_message.reply_text(
                f'⚠️ Nama sudah ada: <code>{esc(duplicate["name"])}</code>\n\nGanti file lama?',
                reply_markup=keyboard([[('✅ Ganti', f'replace:{token}'), ('⏭️ Lewati', f'skip:{token}')]]),
                parse_mode='HTML')
        try: s.add(doc.file_name, doc.file_id)
        except ValueError as e: return await u.effective_message.reply_text(f'❌ {esc(e)}', parse_mode='HTML')
        if mode == 'add': c.user_data.clear()
        return await u.effective_message.reply_text(
            f'✅ Ditambahkan: <code>{esc(doc.file_name[:-3])}</code>',
            reply_markup=admin_menu() if mode == 'add' else keyboard([[('✅ Selesai', 'done')]]),
            parse_mode='HTML')

    await u.effective_message.reply_text(WELCOME, reply_markup=main_menu(), parse_mode='HTML')


async def broadcast(c, source):
    from telegram.error import Forbidden, RetryAfter, TelegramError
    sent = failed = 0
    try:
        for uid in store(c).users():
            for attempt in range(3):
                try:
                    await c.bot.copy_message(chat_id=uid, from_chat_id=source[0], message_id=source[1])
                    sent += 1; break
                except Forbidden:
                    store(c).deactivate(uid); failed += 1; break
                except RetryAfter as e:
                    if attempt == 2: failed += 1; break
                    delay = e.retry_after.total_seconds() if hasattr(e.retry_after, 'total_seconds') else e.retry_after
                    await asyncio.sleep(delay + 0.2)
                except TelegramError:
                    failed += 1; break
            await asyncio.sleep(0.08)
        await c.bot.send_message(
            chat_id=c.bot_data['owner'],
            text=f'✅ <b>BROADCAST SELESAI</b>\n\n✅ Berhasil: {sent}\n❌ Gagal: {failed}',
            parse_mode='HTML')
    finally:
        c.bot_data['broadcast_running'] = False


async def error_handler(u, c):
    log.error('Update failed: %s', type(c.error).__name__)
    if u and u.effective_message:
        try:
            await u.effective_message.reply_text('⚠️ Ada gangguan sementara. Coba lagi atau ketik /start.', parse_mode='HTML')
        except Exception: pass


async def post_init(app):
    await app.bot.set_my_commands([('start', '📱 Menu utama'), ('cancel', '↩️ Batalkan input')])
    log.info('Bot ready @%s', app.bot.username)


def build_application(token, admin_id, db_path):
    app = Application.builder().token(token).concurrent_updates(False).post_init(post_init).build()
    app.bot_data.update(store=Store(db_path), owner=int(admin_id))
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('cancel', start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, on_message))
    app.add_error_handler(error_handler)
    return app


def main():
    load_dotenv()
    token = os.environ.get('BOT_TOKEN', '')
    if not token or not os.environ.get('ADMIN_ID'):
        raise RuntimeError('BOT_TOKEN dan ADMIN_ID wajib diatur')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = build_application(token, int(os.environ['ADMIN_ID']), os.environ.get('DB_PATH', 'data/bot.db'))
    app.run_polling(allowed_updates=['message', 'callback_query'], drop_pending_updates=False)


if __name__ == '__main__': main()
