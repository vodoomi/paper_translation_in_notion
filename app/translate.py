import os
import re
import requests
from dotenv import load_dotenv
import base64
import asyncio
import functools
from time import time
from typing import List, Tuple

from mistralai import Mistral
from mistralai.models import OCRResponse
import google.generativeai as genai
from markdown_it import MarkdownIt


class Translator:
    """
    PDFファイルをmarkdownに変換し、翻訳するクラス

    Args:
        gemini_model_name (str): モデル名

    Attributes:
        genai_api_key (str): GenAI APIキー
        model (genai.GenerativeModel): GenAIのモデル
        gyazo_access_token (str): Gyazoアクセストークン
        mistral_api_key (str): Mistral APIキー
        mistral (Mistral): MistralのAPI
        mistral_model_name (str): Mistralのモデル名
        header_position (dict): 
            ヘッダーの位置
            (key: 何個目のヘッダーか, value: 何行目か)
            ex. {0: 0, 1: 5, 2: 8, 3: 12}
        header_n_words (dict):
            各ヘッダーより前の単語数
            (key: 何個目のヘッダーか, value: そのヘッダーより前の単語数)
            ex. {0: 0, 1: 20, 2: 30, 3: 40}
        images_dict (dict):
            画像の辞書
            (key: 画像名, value: 画像のbase64)
            ex. {'img1': 'base64_str1', 'img2': 'base64_str2'}
    """
    def __init__(self, gemini_model_name: str, mistral_model_name: str):
        load_dotenv()
        self.genai_api_key = os.getenv("GEMINI_API_KEY")
        assert self.genai_api_key, "You need to set the GEMINI_API_KEY environment variable."
        genai.configure(api_key=self.genai_api_key)
        self.model = genai.GenerativeModel(model_name=gemini_model_name)
        self.gyazo_access_token = os.getenv("GYAZO_ACCESS_TOKEN")
        assert self.gyazo_access_token, "You need to set the GYAZO_ACCESS_TOKEN environment variable."
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        assert self.mistral_api_key, "You need to set the MISTRAL_API_KEY environment variable."
        self.mistral = Mistral(self.mistral_api_key)
        self.mistral_model_name = mistral_model_name
        self.header_position = {}
        self.header_n_words = {}
        self.images_dict = {}

    def pdf_to_markdown(self, pdf_url: str) -> str:
        ocr_response = self.mistral.ocr.process(
            model=self.mistral_model_name,
            document={
                "type": "document_url",
                "document_url": pdf_url
            },
            include_image_base64=True,
        )
        # ページごとに分かれているOCR結果を結合
        md = self.get_combined_markdown(ocr_response)
        return md

    def get_combined_markdown(self, ocr_response: OCRResponse) -> str:
        markdowns: list[str] = []
        self.images_dict = {}
        for page in ocr_response.pages:
            for image in page.images:
                self.images_dict[image.id] = image.image_base64
            markdowns.append(page.markdown)
        return "\n\n".join(markdowns)
        
    def get_header_position(self, md: str):
        # ヘッダー位置を抽出する正規表現
        header_pattern = r'(#+)'
        # ヘッダー位置、単語数を抽出
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

    # 同期的な処理を非同期で呼び出すためのヘルパー関数
    async def generate_content_async(self, model, prompt, md_chunk):
        loop = asyncio.get_running_loop()
        # 同期メソッド model.generate_content をスレッドプールで実行
        result = await loop.run_in_executor(
            None,
            # generation_configのようにキーワードを指定した引数を使用するため、functools.partialを使う
            functools.partial(
                model.generate_content,
                [prompt, md_chunk],
                generation_config=genai.GenerationConfig(
                    temperature=0
                )
            )
        )
        return result


    async def process_md_chunks(self, model, prompt, split_md_list):
        # API 呼び出し結果を一時的に格納するリスト
        md_jp_list = []

        # すべての md_chunk について並列に処理させる
        tasks = []
        for md in split_md_list:
            md_chunk = "\n".join(md)
            tasks.append(self.generate_content_async(model, prompt, md_chunk))

        # 非同期で全タスクを実行して結果をまとめる
        results = await asyncio.gather(*tasks)

        for res in results:
            print(res.usage_metadata)  # ログ出力や解析などに利用
            md_jp_list.append(res.text)

        # すべてのテキストを結合
        md_jp = "\n".join(md_jp_list)
        return md_jp

    def translate_markdown(self, prompt: str, md: str, max_words: int, gyazo_endpoint: str) -> str:
        # 表を除去
        plain_md, tables = self.split_md(md)
        # ヘッダーの位置を取得
        self.get_header_position(md)
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
        split_md = plain_md.splitlines()
        split_md_list = [split_md[i:j] for i, j in zip([0]+split_row_list, split_row_list+[None])]
        # 各分割したmdに対して翻訳
        start = time()
        # イベントループ上で処理関数を実行
        md_jp = asyncio.run(self.process_md_chunks(self.model, prompt, split_md_list))
        end = time()
        print(f"Translation time: {end - start:.2f} seconds")
        # 画像をgyazoから参照できるURLに置き換え
        md_jp = self.replace_images_in_markdown(md_jp, self.images_dict, gyazo_endpoint)
        # 表を元に戻す
        md_jp = self.merge_tables(md_jp, md, tables)
        return md_jp
    
    def replace_images_in_markdown(self, markdown_str: str, images_dict: dict, gyazo_endpoint: str) -> str:
        for img_name, base64_str in images_dict.items():
            url = self.upload_img_to_gyazo(base64_str, gyazo_endpoint)
            markdown_str = markdown_str.replace(
                f"![{img_name}]({img_name})", url)
        return markdown_str
    
    def upload_img_to_gyazo(self, img_base64: str, gyazo_endpoint: str):
        img_binary = base64.b64decode(img_base64.split(',')[1])
        response = requests.post(
            gyazo_endpoint,
            files={'imagedata': img_binary},
            data={'access_token': self.gyazo_access_token}
        )
        url = response.json()['url']
        return url
    

    def split_md(self, md_text: str) -> Tuple[str, List[Tuple[int, int]]]:
        """
        表ブロックだけ除外しつつ、'#' 見出しを含むすべての行を保持する。
        
        Returns
        -------
        plain_md : str
            表を除去した Markdown 全体
        tables   : List[(start, end)]
            除外した表の行範囲 (0-index, end は non-inclusive)
        """
        md = MarkdownIt("commonmark", {"tables": True})
        tokens = md.parse(md_text)

        # ① 表の行範囲を抽出
        table_ranges: List[Tuple[int, int]] = []
        stack: List[int] = []

        for tok in tokens:
            if tok.type == "table_open":
                # tok.map → (line_start, line_end) ただし end は table_open の行と同じなので使わない
                stack.append(tok.map[0])
            elif tok.type == "table_close":
                start = stack.pop()
                end = tok.map[1]           # table_close.map[1] はブロック直後の行
                table_ranges.append((start, end))

        # ② 行ごとに「残す／捨てる」を判定
        lines = md_text.splitlines(keepends=True)
        keep = [True] * len(lines)
        for s, e in table_ranges:
            for i in range(s, e):
                keep[i] = False

        # ③ 再構成（見出しの '#' も完全保持）
        plain_md = "".join(line for i, line in enumerate(lines) if keep[i])
        return plain_md, table_ranges
    

    def merge_tables(self, plain_md: str, md_orig: str, table_ranges):
        lines_orig = md_orig.splitlines(keepends=True)
        plain_lines = plain_md.splitlines(keepends=True)

        # plain_lines に表を挿入していく
        offset = 0
        for s, e in sorted(table_ranges):
            table_block = "".join(lines_orig[s:e])
            insert_at = s - offset  # plain_lines は表行が削れている分だけ短い
            plain_lines.insert(insert_at, table_block)
            offset += (e - s)
        return "".join(plain_lines)
