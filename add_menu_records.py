from __future__ import print_function
import datetime
import pickle
import os
from os.path import join, dirname
from dotenv import load_dotenv
from functools import reduce

from notion.client import NotionClient
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

token_v2 = os.environ.get("TOKEN")
url = os.environ.get("MENU_DATABASE_URL")
calendarId = os.environ.get("CALENDAR_ID")

# Notion
client = NotionClient(token_v2)


def create_menu_record(cv, record):
    print(record)
    row = cv.collection.add_row()
    row.when = record['when']
    row.date = record['date']
    row.date.reminder = {"unit": "minute", "value": 30}


def main():
    cv = client.get_collection_view(url)

    today = datetime.date.today()
    count = 1
    record_base = [{'when': '朝食', 'time': 8}, {
        'when': '昼食', 'time': 12}, {'when': '夜食', 'time': 18}]

    menu_records = list(
        reduce(
            lambda a,
            b: a +
            b,
            list(
                map(
                    lambda i: list(
                        map(
                            lambda v: {
                                'when': v['when'],
                                'date': datetime.datetime.combine(
                                    today +
                                    datetime.timedelta(
                                        days=i),
                                    datetime.time(
                                        v['time']))},
                            record_base)),
                    range(count)))))
    # TODO 作成済みのレコードは除外したい、前回の最新の次のものから作るでも良いかも

    for r in menu_records:
        create_menu_record(cv, r)


if __name__ == '__main__':
    main()
