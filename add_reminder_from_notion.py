from __future__ import print_function
import datetime
import pickle
import sys
import os
from os.path import join, dirname
from dotenv import load_dotenv
from abc import ABCMeta, abstractmethod

from notion.client import NotionClient
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

args = sys.argv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
token_v2 = os.environ.get("TOKEN")

# Notion
client = NotionClient(token_v2)

# Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

creds = None
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('calendar', 'v3', credentials=creds)


def fetch_new_records(cv, now):
    return cv.collection.get_rows()


def fetch_calendars(now):
    time_min = now.isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime').execute()
    event_names = list(
        map(lambda e: e['summary'], events_result.get('items', [])))

    if not event_names:
        print('No upcoming events found.')
    return event_names


def create_calendar(event, calendarId):
    print('新しいリマインダー: ')
    print(event)
    event = service.events().insert(calendarId=calendarId, body=event).execute()
    return event['id']
    # TODO 失敗しても例外復帰させる


class TableOperation(metaclass=ABCMeta):
    @abstractmethod
    def filter_records(self):
        # 関数化する必要ないかも
        pass

    def generate_event(self):
        pass


class ToDoOperation(TableOperation):
    url = os.environ.get("TODO_URL")
    calendar_id = os.environ.get("TODO_CALENDAR_ID")
    calendar_log_file = 'logs/todo_calendar.txt'

    def filter_records(self, records, now, logs):
        return list(
            filter(
                lambda task: task.deadline and datetime.datetime.combine(
                    task.deadline.start,
                    datetime.time(0)) > now and task.name not in fetch_calendars(now),
                records))

    def generate_event(self, record):
        # TODO eventではなくreminderにしたい
        return {
            'summary': record.name,
            'description': 'Notionからの自動連携',
            'start': {
                'date': str(record.deadline.start),
            },
            'end': {
                'date': str(record.deadline.start),
            },
        }


class MenuOperation(TableOperation):
    url = os.environ.get("MENU_URL")
    calendar_id = os.environ.get("MENU_CALENDAR_ID")
    calendar_log_file = 'logs/menu_calendar.txt'

    def filter_records(self, records, now, logs):
        return list(
            filter(
                lambda menu: menu.date and
                datetime.datetime.combine(
                    menu.date.start,
                    datetime.time(0)) > now
                    and menu.id not in logs,
                records))

    def generate_event(self, record):
        if record.when == '朝食':
            date = datetime.datetime.combine(
                record.date.start, datetime.time(8))
        elif record.when == '昼食':
            date = datetime.datetime.combine(
                record.date.start, datetime.time(12))
        else:
            date = datetime.datetime.combine(
                record.date.start, datetime.time(18))

        return {
            'summary': '[{when}] {menu}'.format(when=record.when, menu=','.join(record.menu)),
            'description': '食材: {ingredients}\nレシピ: {recipe}\n※Notionからの自動連携'.format(ingredients=','.join(record.ingredients), recipe=record.recipe),
            # TODO 残しておく食材も書きたい
            'start': {
                'dateTime': date.isoformat(),
                'timeZone': 'Japan',
            },
            'end': {
                'dateTime': date.isoformat(),
                'timeZone': 'Japan',
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": 'email',
                        "minutes": 10
                    }
                ]
            }
        }


def main(operation_key):
    if operation_key == 'todo':
        operation = ToDoOperation()
    elif operation_key == 'menu':
        operation = MenuOperation()
    else:
        raise Exception('オペレーション名の指定が間違っている')

    cv = client.get_collection_view(operation.url)
    now = datetime.datetime.utcnow()

    f = open(operation.calendar_log_file, 'r+')
    target_records = operation.filter_records(fetch_new_records(cv, now), now, list(map(lambda v: v[:-1], f.readlines())))

    if len(target_records) > 0:
        for record in target_records:
            calendar_id = create_calendar(
                operation.generate_event(record),
                operation.calendar_id)
            print(calendar_id)
            f.write(f'{record.id}\n')
            # calendar_idも記録する
            # TODO 更新することも可能にしたい
    else:
        print('カレンダー作成なし')
    f.close()


if __name__ == '__main__':
    if len(args) == 2:
        main(args[1])
    else:
        raise Exception('引数の数が違う')
