import os
from dotenv import load_dotenv

from pix2text import Pix2Text
import google.generativeai as genai


class Translator:
    def __init__(self, model_name: str):
        load_dotenv()
        self.genai_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.genai_api_key)
        self.model = genai.GenerativeModel(model_name=model_name)

    def pdf_to_markdown(self, pdf_path: str, output_path: str = "", debug: bool = False):
        p2t = Pix2Text.from_config(enable_table=False)
        page_numbers = [0, 1, 2] if debug else None
        doc = p2t.recognize_pdf(pdf_path, page_numbers=page_numbers)
        md = doc.to_markdown(output_path, markdown_fn=None)
        return md

    def translate_markdown(self, prompt: str, md: str):
        result = self.model.generate_content(
            [prompt, md], 
            generation_config=genai.GenerationConfig(
                temperature=0
            )
        )
        return result.text
