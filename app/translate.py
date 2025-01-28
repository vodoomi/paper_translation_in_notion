import os
import re
from glob import glob
import requests
from dotenv import load_dotenv

from pix2text import Pix2Text
import google.generativeai as genai


class Translator:
    def __init__(self, model_name: str):
        load_dotenv()
        self.genai_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.genai_api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.gyazo_access_token = os.getenv("GYAZO_ACCESS_TOKEN")
        self.image_urls = []
        self.header_position = {}
        self.image_position = []

    def pdf_to_markdown(self, pdf_path: str, output_dir: str = "../output/", gyazo_endpoint: str = "https://upload.gyazo.com/api/upload", debug: bool = False):
        p2t = Pix2Text.from_config(enable_table=False)
        page_numbers = [3, 4, 5, 6] if debug else None
        doc = p2t.recognize_pdf(pdf_path, page_numbers=page_numbers)
        # markdown_fn=Noneでmarkdownファイルを保存しない
        md = doc.to_markdown(output_dir, markdown_fn=None)

        # 画像URLに対する処理
        md = self.preprocess_img_url(md, output_dir, gyazo_endpoint)
        return md
    
    def preprocess_img_url(self, md: str, output_dir: str, gyazo_endpoint: str):
        # 画像URLとヘッダー位置を抽出する正規表現
        image_pattern = r'!\[.*?\]\((.*?\.jpg)\)'
        header_pattern = r'(#+)'

        # 画像URLとヘッダー位置を抽出
        header_count = 0
        for i, line in enumerate(md.splitlines()):
            header_match = re.match(header_pattern, line)
            if header_match:
                self.header_position[header_count] = i
                header_count += 1

            image_match = re.search(image_pattern, line)
            if image_match:
                img_path = output_dir + image_match.group(1)
                img_url = self.upload_img_to_gyazo(img_path, gyazo_endpoint)
                self.image_urls.append(img_url)
                self.image_position.append(i)

        # image_postionが所属しているheader_positionを取得
        for i, image_pos in enumerate(self.image_position):
            for j in range(len(self.header_position)-1, -1, -1):
                if image_pos > self.header_position[j]:
                    self.image_position[i] = j
                    break

        # 画像URLを削除
        md = re.sub(image_pattern+"\n", '', md)

        return md
    
    def upload_img_to_gyazo(self, img_path: str, gyazo_endpoint: str):
        with open(img_path, 'rb') as file:
            response = requests.post(
                gyazo_endpoint,
                files={'imagedata': file},
                data={'access_token': self.gyazo_access_token}
            )
        url = response.json()['url']
        return url

    def translate_markdown(self, prompt: str, md: str):
        result = self.model.generate_content(
            [prompt, md], 
            generation_config=genai.GenerationConfig(
                temperature=0
            )
        )
        return result.text
    
    def replace_img_url(self, md: str):
        md_lines = md.splitlines()
        header_pattern = r'(#+)'

        header_count = 0
        for i, line in enumerate(md_lines):
            header_match = re.match(header_pattern, line)
            if header_match:
                if header_count in self.image_position:
                    img_url = self.image_urls[self.image_position.index(header_count)]
                    md_lines.insert(i+1, img_url)
                header_count += 1

        return '\n'.join(md_lines)
