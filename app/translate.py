import os
import re
from glob import glob
import requests
from dotenv import load_dotenv

from pix2text import Pix2Text
import google.generativeai as genai


class Translator:
    """
    PDFファイルをmarkdownに変換し、翻訳するクラス

    Args:
        model_name (str): モデル名

    Attributes:
        genai_api_key (str): GenAI APIキー
        model (genai.GenerativeModel): GenAIのモデル
        gyazo_access_token (str): Gyazoアクセストークン
        image_urls (list): 画像URLのリスト
        header_position (dict): 
            ヘッダーの位置
            (key: 何個目のヘッダーか, value: 何行目か)
            ex. {0: 0, 1: 5, 2: 8, 3: 12}
        header_n_words (dict):
            各ヘッダーより前の単語数
            (key: 何個目のヘッダーか, value: そのヘッダーより前の単語数)
            ex. {0: 0, 1: 20, 2: 30, 3: 40}
        image_position (list): 
            画像の位置 -> 所属しているヘッダーが何個目か
            ex. [6, 10, 11] -> [1, 2, 2]
    """
    def __init__(self, model_name: str):
        load_dotenv()
        self.genai_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.genai_api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.gyazo_access_token = os.getenv("GYAZO_ACCESS_TOKEN")
        self.image_urls = []
        self.header_position = {}
        self.header_n_words = {}
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

        # 画像URLとヘッダー位置、単語数を抽出
        header_count = 0
        total_n_words = 0
        for i, line in enumerate(md.splitlines()):
            header_match = re.match(header_pattern, line)
            if header_match:
                self.header_position[header_count] = i
                self.header_n_words[header_count] = total_n_words
                header_count += 1
            n_words = line.count(' ') + 1 if line.strip() else 0
            total_n_words += n_words

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
        md = re.sub(image_pattern, '', md)

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

    def translate_markdown(self, prompt: str, md: str, max_words: int):
        # 単語数が上限を超えるヘッダーを取得
        split_idx_list = []
        for max_words_ in range(max_words, max(self.header_n_words.values()), max_words):
            for k, v in self.header_n_words.items():
                if v > max_words_:
                    split_idx_list.append(k)
                    break
        # ヘッダーの開始行を取得
        split_row_list = [self.header_position[i] for i in split_idx_list]
        # mdを分割
        split_md = md.splitlines()
        split_md_list = [split_md[i:j] for i, j in zip([0]+split_row_list, split_row_list+[None])]
        # 各分割したmdに対して翻訳
        md_jp_list = []
        for md in split_md_list:
            md = '\n'.join(md)
            result = self.model.generate_content(
                [prompt, md], 
                generation_config=genai.GenerationConfig(
                    temperature=0
                )
            )
            print(result.usage_metadata)
            md_jp_list.append(result.text)
        return '\n'.join(md_jp_list)
    
    def replace_img_url(self, md: str):
        md_lines = md.splitlines()
        header_pattern = r'(#+)'

        header_count = 0
        for i, line in enumerate(md_lines):
            header_match = re.match(header_pattern, line)
            if header_match:
                # 各ヘッダーに所属する画像のインデックスを取得
                img_idx = [i for i, pos in enumerate(self.image_position) if pos == header_count]
                # 画像のインデックスを逆順にする
                img_idx.reverse()
                # 画像URLを挿入
                img_urls = [self.image_urls[i] for i in img_idx]
                for img_url in img_urls:
                    md_lines.insert(i+1, img_url)
                header_count += 1

        return '\n'.join(md_lines)
