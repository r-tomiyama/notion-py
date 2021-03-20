from __future__ import print_function
import datetime
import pickle
import os
from os.path import join, dirname
from dotenv import load_dotenv

from notion.client import NotionClient
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

token_v2 = os.environ.get("TOKEN")
url = os.environ.get("TODO_DATABASE_URL")
calendarId = os.environ.get("CALENDAR_ID")

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


def fetch_tasks():
    result = client.get_collection_view(url)
    # TODO now以降のものにフィルターする
    return list(filter(lambda row: row.deadline, result.collection.get_rows()))


def fetch_calendars(now):
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=100, singleEvents=True,
                                          orderBy='startTime').execute()
    event_names = list(
        map(lambda e: e['summary'], events_result.get('items', [])))

    if not event_names:
        print('No upcoming events found.')
    return event_names


def create_calendar(name, date):
    # TODO eventではなくreminderにしたい
    event = {
        'summary': name,
        'description': 'Notionからの自動連携',
        'start': {
            'date': date,
        },
        'end': {
            'date': date,
        },
    }

    print('新しいリマインダー: ' + name + ', ' + date)
    event = service.events().insert(calendarId=calendarId, body=event).execute()
    print(event['id'])
    # TODO 失敗しても例外復帰させる


def main():
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    targets = list(
        filter(
            lambda task: task.name not in fetch_calendars(now),
            fetch_tasks()))

    if len(targets) > 0:
        for task in targets:
            create_calendar(task.name, str(task.deadline.start))
            # TODO 更新も可能にしたい
    else:
        print('リマインダー作成なし')


if __name__ == '__main__':
    main()
