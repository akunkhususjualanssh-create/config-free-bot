import asyncio,json
from dotenv import load_dotenv
import os
from telegram import Bot

async def main():
    load_dotenv()
    async with Bot(os.environ['BOT_TOKEN']) as b:
        me=await b.get_me(); hook=await b.get_webhook_info()
        print(json.dumps({'id':me.id,'username':me.username,'webhook_present':bool(hook.url)}))
        if hook.url: raise RuntimeError('Existing webhook found; not replacing')
        await b.set_my_name('Config Free')
        await b.set_my_description('Download config .hc gratis. Pilih Config free untuk mengambil file atau hubungi admin untuk order.')
        await b.set_my_commands([('start','Menu utama'),('cancel','Batalkan input')])
        print(json.dumps({'name':(await b.get_my_name()).name,'description':(await b.get_my_description()).description,'commands':[x.command for x in await b.get_my_commands()]}))
asyncio.run(main())
