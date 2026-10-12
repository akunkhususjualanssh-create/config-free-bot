import asyncio,os,json
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import Forbidden
from bot import main_menu
async def main():
    load_dotenv()
    async with Bot(os.environ['BOT_TOKEN']) as b:
        try:
            m=await b.send_message(chat_id=int(os.environ['ADMIN_ID']),text='Config Free sudah aktif. Gunakan Menu admin -> Add config untuk upload file .hc. Atur nomor WhatsApp melalui Atur kontak admin.',reply_markup=main_menu())
            check=await b.edit_message_reply_markup(chat_id=m.chat.id,message_id=m.message_id,reply_markup=main_menu())
            print(json.dumps({'sent_message_id':m.message_id,'chat_id':m.chat.id,'buttons':[[x.text for x in r] for r in m.reply_markup.inline_keyboard]}))
        except Forbidden:
            print('OWNER_MUST_START_BOT_FIRST')
        except Exception as e:
            if 'not modified' in str(e).lower():
                print(json.dumps({'sent_message_id':m.message_id,'chat_id':m.chat.id,'markup_verified':'Telegram confirmed message not modified'}))
            else: print('CHECK_ERROR',type(e).__name__,str(e).replace(os.environ['BOT_TOKEN'],'[REDACTED]'))
asyncio.run(main())
