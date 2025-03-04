from pyrogram import Client
import asyncio
import os
from dotenv import load_dotenv
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


load_dotenv()


api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')


app = Client(
    "my_account",
    api_id=api_id,
    api_hash=api_hash,
    workdir=SCRIPT_DIR
)

async def process_chat_link(chat_link):
    """
    Обрабатываем разные форматы ссылок и идентификаторов чатов
    """
    try:

        chat_link = chat_link.strip()


        if '+' in chat_link:
            return {'type': 'invite', 'link': chat_link}


        if 'web.telegram.org' in chat_link:
            match = re.search(r'#(-?\d+)', chat_link)
            if match:
                chat_id = int(match.group(1))
                return {'type': 'id', 'id': chat_id}
        

        elif 't.me/' in chat_link:
            username = chat_link.split('t.me/')[-1]
            if username.startswith('+'):
                return {'type': 'invite', 'link': chat_link}
            return {'type': 'username', 'username': username}
        

        elif chat_link.replace('-', '').isdigit():
            chat_id = int(chat_link)
            return {'type': 'id', 'id': chat_id}
        

        elif chat_link.startswith('@'):
            return {'type': 'username', 'username': chat_link[1:]}
        

        return {'type': 'raw', 'text': chat_link}

    except Exception as e:
        print(f"❌ Ошибка обработки ссылки {chat_link}: {str(e)}")
        return None

async def join_and_get_chat(chat_data):
    """Присоединяемся к чату и получаем его идентификатор"""
    try:
        if chat_data['type'] == 'invite':

            try:

                chat = await app.join_chat(chat_data['link'])
                await asyncio.sleep(2)  
                return chat.id
            except Exception as e:
                print(f"⚠️ Информация: {str(e)}")

                try:

                    chat = await app.get_chat(chat_data['link'])
                    return chat.id
                except Exception as e2:
                    print(f"⚠️ Не удалось получить чат после ошибки присоединения: {str(e2)}")
                    try:

                        async for dialog in app.get_dialogs():
                            if dialog.chat.invite_link == chat_data['link']:
                                return dialog.chat.id
                    except Exception as e3:
                        print(f"⚠️ Не удалось найти чат в диалогах: {str(e3)}")
                    return None

        elif chat_data['type'] == 'username':

            try:

                chat = await app.get_chat(chat_data['username'])
                return chat.id
            except Exception:
                try:

                    chat = await app.join_chat(chat_data['username'])
                    await asyncio.sleep(2)
                    return chat.id
                except Exception as e:
                    print(f"⚠️ Ошибка при работе с чатом по юзернейму: {str(e)}")
                    return None

        elif chat_data['type'] == 'id':

            try:
                chat = await app.get_chat(chat_data['id'])
                return chat.id
            except Exception as e:
                print(f"⚠️ Ошибка при получении чата по ID: {str(e)}")

                try:
                    async for dialog in app.get_dialogs():
                        if dialog.chat.id == chat_data['id']:
                            return dialog.chat.id
                except Exception as e2:
                    print(f"⚠️ Не удалось найти чат в диалогах: {str(e2)}")
                return None

        elif chat_data['type'] == 'raw':

            for attempt in [
                lambda: app.get_chat(chat_data['text']),
                lambda: app.join_chat(chat_data['text'])
            ]:
                try:
                    chat = await attempt()
                    return chat.id
                except Exception:
                    continue
            

            try:
                async for dialog in app.get_dialogs():
                    if str(dialog.chat.id) == chat_data['text']:
                        return dialog.chat.id
            except Exception as e:
                print(f"⚠️ Не удалось найти чат в диалогах: {str(e)}")
            
            print(f"⚠️ Не удалось получить доступ к чату: {chat_data['text']}")
            return None

    except Exception as e:
        print(f"❌ Общая ошибка при обработке чата: {str(e)}")
        return None

async def send_messages():

    chats_file = os.path.join(SCRIPT_DIR, 'chats.txt')
    messages_file = os.path.join(SCRIPT_DIR, 'messages.txt')
    

    if not os.path.exists(chats_file):
        print(f"❌ Файл не найден: {chats_file}")
        return
        
    if not os.path.exists(messages_file):
        print(f"❌ Файл не найден: {messages_file}")
        return


    with open(chats_file, 'r', encoding='utf-8') as f:
        chats = [line.strip() for line in f if line.strip()]
    

    with open(messages_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()

        messages = [msg.strip() for msg in content.split('===') if msg.strip()]
    
    if not chats:
        print("❌ Нет доступных чатов!")
        return
    
    if not messages:
        print("❌ Нет сообщений для отправки!")
        return

    print(f"📱 Загружено {len(chats)} чатов и {len(messages)} сообщений")
    
    while True:
        for chat_link in chats:
            print(f"\n🔄 Обрабатываем чат: {chat_link}")
            

            chat_data = await process_chat_link(chat_link)
            if not chat_data:
                print(f"❌ Не удалось обработать ссылку: {chat_link}")
                continue
            
            print(f"📨 Тип чата: {chat_data['type']}")
            

            chat_id = await join_and_get_chat(chat_data)
            if not chat_id:
                print(f"❌ Не удалось получить доступ к чату: {chat_link}")
                continue

            try:

                chat_info = await app.get_chat(chat_id)
                print(f"✅ Успешно подключились к чату: {chat_info.title} (тип: {chat_info.type})")
            except Exception as e:
                print(f"⚠️ Не удалось получить информацию о чате: {str(e)}")
            

            for message in messages:
                try:

                    await app.send_message(chat_id, message)
                    print(f"✅ Сообщение успешно отправлено в {chat_link}")

                    preview = message.replace('\n', ' ')[:50] + ('...' if len(message) > 50 else '')
                    print(f"📨 Превью: {preview}")
                except Exception as e:
                    print(f"❌ Ошибка отправки: {str(e)}")
                

                print("⏳ Ждем 15 секунд...")
                await asyncio.sleep(15)
            

            print("⏳ Ждем 15 секунд перед следующим чатом...")
            await asyncio.sleep(15)

async def main():
    try:
        print("🚀 Запускаем спамер...")
        await app.start()
        me = await app.get_me()
        print(f"✅ Вошли как: {me.first_name} (@{me.username})")
        await send_messages()
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
    finally:
        await app.stop()

if __name__ == '__main__':
    app.run(main())

