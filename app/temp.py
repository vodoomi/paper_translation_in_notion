from translate import Translator
from notion import NotionWriter
from cfg import cfg

translator = Translator(cfg.model_name)
md = translator.pdf_to_markdown("../input/bertopic.pdf", cfg.output_dir, cfg.gyazo_endpoint, True)
md_jp = translator.translate_markdown(cfg.prompt, md)
md_jp = translator.replace_img_url(md_jp)

notion = NotionWriter()
notion.get_pages_from_database()
notion.make_nest_page(cfg.target_title, md_jp)
