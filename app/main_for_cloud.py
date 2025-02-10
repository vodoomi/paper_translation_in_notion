import requests

from translate import Translator
from notion import NotionWriter
from cfg import cfg

if __name__ == "__main__":
    # 未翻訳ページの取得
    notion = NotionWriter()
    notion.get_untranslated_page()
    title, url = notion.get_title_and_url()
    response = requests.get(url)
    response.raise_for_status()
    url = response.content

    # PDFの翻訳
    translator = Translator(cfg.model_name)
    md = translator.pdf_to_markdown(url, cfg.output_dir, cfg.gyazo_endpoint)
    md_jp = translator.translate_markdown(cfg.prompt, md, cfg.max_input_words)
    md_jp = translator.replace_img_url(md_jp)

    # Notion にページを作成
    notion.make_nest_page(md_jp)
    notion.input_translated_completed()
