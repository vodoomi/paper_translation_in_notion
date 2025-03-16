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
        # 未翻訳ページの取得
        notion = NotionWriter()
        notion.get_untranslated_page()
        title, url = notion.get_title_and_url()

        # # PDFの翻訳
        translator = Translator(cfg.model_name, cfg.mistral_model_name)
        md = translator.pdf_to_markdown(url)
        md_jp = translator.translate_markdown(cfg.prompt, md, cfg.max_input_words, cfg.gyazo_endpoint)

        # Notion にページを作成
        notion.make_nest_page(md_jp)
        notion.input_translated_completed()
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
