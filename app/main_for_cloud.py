from translate import Translator
from notion import NotionWriter
from cfg import cfg

if __name__ == "__main__":
    # 未翻訳ページの取得
    notion = NotionWriter()
    notion.get_untranslated_page()
    _, url = notion.get_title_and_url()

    # # PDFの翻訳
    translator = Translator(cfg.model_name, cfg.mistral_model_name)
    md = translator.pdf_to_markdown(url)
    md_jp = translator.translate_markdown(cfg.prompt, md, cfg.max_input_words, cfg.gyazo_endpoint)

    # Notion にページを作成
    notion.make_nest_page(md_jp)
    notion.input_translated_completed()
