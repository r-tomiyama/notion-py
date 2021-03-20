import os
from os.path import join, dirname
from dotenv import load_dotenv

from notion.client import NotionClient

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

token_v2 = os.environ.get("TOKEN")
url = os.environ.get("SAMPLE_URL")

client = NotionClient(token_v2)

# titleの書き換え
page = client.get_block(url)
print("The old title is:", page.title)
page.title = "The title has now changed, and has *live-updated* in the browser!"

# データベースの取得
cv = client.get_collection_view(url)
for row in cv.collection.get_rows():
    print(row.name)
