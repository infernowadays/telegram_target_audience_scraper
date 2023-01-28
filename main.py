import configparser
import time
from datetime import timedelta

from telethon import TelegramClient, errors
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.channels import *
from telethon.tl.functions.messages import (GetHistoryRequest)
from telethon.tl.types import *

# Reading Configs
config = configparser.ConfigParser()
config.read("config.ini")

# Setting configuration values
api_id = int(config['Telegram']['api_id'])
api_hash = str(config['Telegram']['api_hash'])

phone = config['Telegram']['phone']
username = config['Telegram']['username']

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)

chats = list(dict.fromkeys(
    [
        'https://t.me/MyOutlineVPN',
        'https://t.me/MyOutlineVPN',
        'https://t.me/MyOutlineVPN'
    ]
))

users_send_messages_last_month_ids = []
filtered_usernames = []


def get_last_month():
    today = datetime.today()
    first = today.replace(day=1)
    return first - timedelta(days=1)


async def auth():
    await client.start()
    print("Client Created")
    # Ensure you're authorized
    if await client.is_user_authorized() is False:
        await client.send_code_request(phone)
        try:
            await client.sign_in(phone, input('Enter the code: '))
        except SessionPasswordNeededError:
            await client.sign_in(password=input('Password: '))


async def main():
    await auth()

    for chat in chats:
        # logger
        print('\n')
        print(str(chats.index(chat) + 1) + '/' + str(len(chats)))
        print('Chat: ' + chat)
        # get chat entity
        if chat.isdigit():
            entity = PeerChannel(int(chat))
        else:
            entity = chat

        # skip chat if alias does not exist
        try:
            chat_entity = await client.get_entity(entity)
        except ValueError as e:
            print('Error: ' + e.args[0])
            print('Chat ' + chat + ' skipped')
            continue

        # get unique user ids by messages for the last month
        offset_id = 0
        limit = 10000
        total_messages = 0
        max_messages_count = 10000
        all_messages = []

        while True:
            # logger
            print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
            # to avoid blocking for frequent requests
            time.sleep(1)
            # noinspection PyTypeChecker
            history = await client(GetHistoryRequest(
                peer=chat_entity,
                offset_id=offset_id,
                offset_date=None,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0
            ))
            chat_messages = list(
                filter(
                    lambda x: datetime(year=x.date.year, month=x.date.month, day=x.date.day) > get_last_month(),
                    history.messages
                )
            )

            if not chat_messages:
                break

            for message in chat_messages:
                all_messages.append(message)
                try:
                    user_id = message.from_id.user_id
                    if user_id not in users_send_messages_last_month_ids:
                        users_send_messages_last_month_ids.append(user_id)
                except AttributeError:
                    pass

            offset_id = chat_messages[len(chat_messages) - 1].id

            total_messages = len(all_messages)
            if total_messages == max_messages_count:
                break

        # filter users
        offset = 0
        all_participants = []
        while True:
            # to avoid blocking for frequent requests
            time.sleep(1)
            # noinspection PyTypeChecker
            participants = await client(GetParticipantsRequest(
                channel=chat_entity,
                filter=ChannelParticipantsRecent(),
                offset=offset,
                limit=limit,
                hash=0
            ))
            if not participants.users:
                break

            all_participants.extend(participants.users)
            offset += len(participants.users)

        filtered_participants = list(
            filter(lambda x:
                   x.deleted is False and
                   x.fake is False and
                   x.restricted is False and
                   x.scam is False and
                   x.support is False and
                   x.bot is False and
                   x.username is not None and
                   isinstance(x.status, UserStatusRecently) and
                   x.id in users_send_messages_last_month_ids,
                   all_participants)
        )

        filtered_usernames.extend([user.username for user in filtered_participants])
        print("Filtered users:", len(filtered_participants))

    # remove duplicates
    unique_usernames = list(dict.fromkeys(filtered_usernames))
    # save filtered usernames to file
    text_file = open('usernames.txt', mode='wt', encoding='utf-8')
    for unique_username in unique_usernames:
        text_file.write('@' + unique_username + '\n')
    text_file.close()


client.loop.run_until_complete(main())
