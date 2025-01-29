import os
import requests
from dotenv import load_dotenv

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from translate import Translator
from notion import NotionWriter
from cfg import cfg

# .env ファイルから環境変数を読み込みます
load_dotenv()

# ボットトークンと署名シークレットを使ってアプリを初期化します
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Notionからのメッセージをリッスンします
@app.message()
def message_hello(message, say):
    use_id = message['user']
    # Notionからメッセージを受信したとき
    if use_id == os.environ.get("NOTION_USER_ID"):
        # タイトル部分を取得
        title = message["blocks"][1]["text"]["text"]
        title = title.split("n=slack|")[-1].split(">*")[0]
        # URL部分を取得
        count = 0
        while True:
            if "リンク" in message["blocks"][1]["fields"][count]["text"]:
                url = message["blocks"][1]["fields"][count]["text"]
                url = url.split("*リンク*\n")[-1].replace("\u200b", "")
                response = requests.get(url)
                response.raise_for_status()
                url = response.content
                break
            count += 1
        # イベントがトリガーされたチャンネルへ say() でメッセージを送信します
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "PDFファイルを処理中です..."}
                }
            ],
            text="PDFファイルを処理中です..."
        )
        translator = Translator(cfg.model_name)
        md = translator.pdf_to_markdown(url, cfg.output_dir, cfg.gyazo_endpoint)
        md_jp = translator.translate_markdown(cfg.prompt, md)
        md_jp = translator.replace_img_url(md_jp)

        notion = NotionWriter()
        notion.get_pages_from_database()
        notion.make_nest_page(title, md_jp)
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "PDFファイルの処理が完了しました！"}
                }
            ],
            text="PDFファイルの処理が完了しました！"
        )
    else:
        pass

# アプリを起動します
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
