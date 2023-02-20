from telethon import TelegramClient, events, sync
from telethon.tl.types import PeerChannel
import datetime
# import sqlite3
import requests
import pymorphy2
import os.path

API_ID = 123
API_HASH = '123'
INFOBOT_TOKEN = 'TOKEN'
INFOBOT_CHANNEL_ID = '123'
TRIGGERS_FILE = f'{os.path.dirname(os.path.abspath(__file__))}/triggers.txt'

chats = {}
triggers = []

@events.register(events.NewMessage(incoming=True))
async def handler(event):
	if type(event.peer_id) is PeerChannel:
		channel_id = int(f'-100{event.to_id.channel_id}')
		if channel_id not in chats:
			# print(f'ID канала "{channel_id}" не отслеживается')
			return
		trigger = find_triggers(event.raw_text)
		if trigger is None:
			return
		chat = chats[channel_id]
		# Message ID, Trigger, Chat title, Message contents, Date received, Link to message
		data = (event.id, trigger, chat[1], event.raw_text, event.date.strftime("%d.%m.%Y %H:%M"), construct_link(chat[0], event.id))
		console_print(data)
		infobot_post(data)

async def get_chats() -> None:
	global chats
	async for i in client.iter_dialogs():
		if not i.archived and i.is_channel and str(i.id) != INFOBOT_CHANNEL_ID:
			chats[i.id] = [i.entity.username, i.entity.title]

def inflect_triggers() -> None:
	global triggers
	inflected = {}
	for i in triggers:
		inflected[i] = []
		parsed = morph.parse(i)[0]
		for j in parsed.lexeme:
			inflected[i].append(j.word)
			if 'ё' in j.word:
				inflected[i].append(j.word.replace('ё', 'е'))
	triggers = inflected

def find_triggers(message: str) -> str:
	message = message.lower().split(' ')
	for k, v in triggers.items():
		for i in v:
			if i in message:
				return k
	return None

def infobot_post(data) -> None:
	msg = f'Сообщение из чата {data[2]}:\n\n{data[3]}\n\nТриггер: {data[1]}\nПерейти: {data[5]}'
	requests.post(url=f'https://api.telegram.org/bot{INFOBOT_TOKEN}/sendMessage', data={'chat_id': INFOBOT_CHANNEL_ID, 'text': msg, 'disable_web_page_preview': True})

def console_print(data) -> None:
	print(*data, sep='\n====\n')

def construct_link(channel_username, message_id):
	if channel_username is None or message_id is None:
		return None
	return f'https://t.me/{channel_username}/{message_id}'

def db_insert(data) -> None:
	cur.execute("INSERT INTO messages VALUES(?, ?, ?, ?, ?, ?)", data)
	db.commit()

db = sqlite3.connect('default.db')
cur = db.cursor()

with open(TRIGGERS_FILE) as f:
	for line in f:
		s = line.rstrip()
		if s == "" or s == " " or s == "\n":
			continue
		triggers.append(s.lower())
if len(triggers) == 0:
	print('Триггеров не задано')
	exit()
morph = pymorphy2.MorphAnalyzer()
inflect_triggers()
client = TelegramClient(f'{os.path.dirname(os.path.abspath(__file__))}/sb_session.session', API_ID, API_HASH)
client.add_event_handler(handler)
client.start()

client.loop.run_until_complete(get_chats())
print('Поиск следующих ключевых слов:', *[i for i in triggers], '\nВ следующих чатах:', *[i[1] for i in chats.values()], sep='\n')
client.run_until_disconnected()
