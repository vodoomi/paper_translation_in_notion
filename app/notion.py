import os
import re

from dotenv import load_dotenv
from notion_client import Client


class NotionWriter:
    def __init__(self):
        load_dotenv()
        self.notion_api_token = os.getenv("NOTION_TOKEN")
        assert self.notion_api_token, "You need to set the NOTION_TOKEN environment variable."
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        assert self.database_id, "You need to set the NOTION_DATABASE_ID environment variable."
        self.notion = Client(auth=self.notion_api_token)
        self.untranslated_page = None

    def get_untranslated_page(self):
        """
        未翻訳のページを取得する。
        """
        response = self.notion.databases.query(
            self.database_id,
            filter={
                "property": "Translate Completed",
                "checkbox": {"equals": False}
            }
        )
        untranslated_pages = response.get("results", [])
        assert len(untranslated_pages) == 1, "There should be only one untranslated page." 
        self.untranslated_page = untranslated_pages[0]

    def get_title_and_url(self):
        """
        未翻訳のページからタイトルとURLを取得する。
        """
        assert self.untranslated_page is not None, "Untranslated page not loaded. Please run get_untranslated_page() first."
        title = self.untranslated_page["properties"]["タイトル"]["title"][0]["plain_text"]
        url = self.untranslated_page["properties"]["リンク"]["url"]
        return title, url
    
    def markdown_to_notion_blocks(self, markdown_text: str, chunk_size: int=2000) -> list:
        """
        Markdown形式のテキストをNotionのブロック形式に変換し、listで返す。
        テーブル( | col1 | col2 | ... ) や数式($$ ... $$)、見出し等を処理する。
        """
        # --- 前準備 ---
        block_math_flag = False
        blocks = []

        # 改行区切りで処理しやすいように行のリストにする
        lines = markdown_text.splitlines()

        # インデックスを手動で動かしながら、テーブル行かどうかを判定
        i = 0
        while i < len(lines):
            raw_line = lines[i]
            # chunk_size を考慮するために一度 chunk 分割
            #   → ただしテーブル行の場合はまとめてパースするので先に判定する
            if self.is_table_line(raw_line):
                # テーブルの開始行とみなし、連続するテーブル行をまとめてパースする
                table_data, used_lines = self.collect_and_parse_table(lines, start_index=i)
                i += used_lines  # テーブル行を一気に消費

                if table_data:
                    # テーブルの Notionブロックを生成して追加
                    table_block = self.build_table_block(table_data)
                    blocks.append(table_block)
                continue
            else:
                # テーブル行じゃない場合、元のロジックでチャンクを切り出して処理
                for chunk_start in range(0, len(raw_line), chunk_size):
                    line = raw_line[chunk_start:chunk_start+chunk_size].strip()
                    if not line:
                        continue

                    if line.startswith("$$"):
                        # ブロック数式の開始/終了フラグをトグル
                        block_math_flag = not block_math_flag
                    elif block_math_flag:
                        # ブロック数式モード中
                        blocks.append({
                            "object": "block",
                            "type": "equation",
                            "equation": {
                                "expression": line
                            }
                        })
                    elif line.startswith("# "):
                        # Heading 1
                        blocks.append({
                            "object": "block",
                            "type": "heading_1",
                            "heading_1": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": line[2:].strip()}
                                }]
                            }
                        })
                    elif line.startswith("## "):
                        # Heading 2
                        blocks.append({
                            "object": "block",
                            "type": "heading_2",
                            "heading_2": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": line[3:].strip()}
                                }]
                            }
                        })
                    elif line.startswith("### "):
                        # Heading 3
                        blocks.append({
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": line[4:].strip()}
                                }]
                            }
                        })
                    elif line.startswith("https://") and line.endswith(".jpg"):
                        # 画像ブロック
                        blocks.append({
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {
                                    "url": line
                                }
                            }
                        })
                    elif line.startswith("- "):
                        # Bulleted List
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": line[2:].strip()}
                                }]
                            }
                        })
                    elif line.startswith("1. "):
                        # Numbered List
                        blocks.append({
                            "object": "block",
                            "type": "numbered_list_item",
                            "numbered_list_item": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": line[3:].strip()}
                                }]
                            }
                        })
                    else:
                        # Paragraph (インライン数式を含む処理)
                        rich_text = self.get_inline_equation_text(line)

                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": rich_text
                            }
                        })

                # 1行進める
                i += 1

        return blocks

    def is_table_line(self, line: str) -> bool:
        """
        シンプルに「テーブルっぽい行」かどうかを判定する。
        例: "| col1 | col2 |"や"| --- | --- |"のように
        行頭が'|'で始まり行末が'|'で終わる場合はテーブル行とみなす。
        """
        stripped = line.strip()
        # 空行は除外
        if not stripped:
            return False
        return (stripped.startswith("|") and stripped.endswith("|"))

    def collect_and_parse_table(self, lines, start_index: int):
        """
        lines[start_index] がテーブル行とみなし、
        連続するテーブル行をすべて読み取って
        2次元リストとして返す。
        戻り値: (table_data, used_line_count)
          - table_data: [["Column 1", "Column 2"], ["Foo", "Bar"], ...]
          - used_line_count: 何行分テーブルを消費したか
        """
        table_lines = []
        idx = start_index
        while idx < len(lines):
            if self.is_table_line(lines[idx]):
                table_lines.append(lines[idx].strip())
                idx += 1
            else:
                break

        used_line_count = len(table_lines)
        if not table_lines:
            return [], 0

        # 実際に table_lines をパースして2次元リスト化する
        table_data = self.parse_markdown_table(table_lines)
        return table_data, used_line_count

    def parse_markdown_table(self, table_lines):
        """
        Markdown形式の表の行リストを受け取り、2次元配列にして返す。
        区切り行(---など)は除外。
        例:
          ["| Column 1 | Column 2 |",
           "|----------|----------|",
           "| Foo      | Bar      |"]
          →
          [
            ["Column 1", "Column 2"],
            ["Foo",      "Bar"]
          ]
        """
        # 区切り行の判定用正規表現(---や:---:など)
        separator_pattern = re.compile(r"^\s*:?-{3,}:?\s*$")

        parsed_data = []
        for line in table_lines:
            # 先頭・末尾の '|' を取り除き、内側を分割
            # 例: "| Foo | Bar |" → ["Foo", "Bar"]
            cells = [c.strip() for c in line.strip('|').split('|')]

            # 区切り行(---, ---|---など)はスキップ
            # すべてのセルが区切りパターンとみなせる場合は除外
            if all(separator_pattern.match(cell.replace(':', '-')) for cell in cells):
                continue

            parsed_data.append(cells)

        return parsed_data

    def build_table_block(self, table_data, has_column_header=True, has_row_header=False):
        """
        2次元配列(table_data)を受け取り、Notionの table ブロックを構成するJSONを返す。
        :param table_data: [["Column 1", "Column 2"], ["Foo", "Bar"], ...]
        :param has_column_header: 一行目をカラムヘッダ表示させるか
        :param has_row_header: 一列目を行ヘッダ表示させるか
        """
        if not table_data:
            return None
        
        row_count = len(table_data)
        col_count = max(len(row) for row in table_data)

        # 子ブロック(=テーブルの行)を作る
        table_row_blocks = []
        for row in table_data:
            # rowは["Column 1", "Column 2", ...]
            cells = []
            for cell_value in row:
                # Notionのリッチテキスト
                cell_text = self.get_inline_equation_text(cell_value)
                cells.append(cell_text)
            table_row_blocks.append({
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": cells
                }
            })

        table_block = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": col_count,
                "has_column_header": has_column_header,
                "has_row_header": has_row_header,
                "children": table_row_blocks
            }
        }
        return table_block
    
    def get_inline_equation_text(self, line: str) -> list:
        """
        インライン数式ブロックを構築する。
        """
        # Paragraph (インライン数式を含む処理)
        inline_math_pattern = re.compile(r"\$(.+?)\$")
        rich_text = []
        cursor = 0
        for match in inline_math_pattern.finditer(line):
            start, end = match.span()
            if start > cursor:
                rich_text.append({
                    "type": "text",
                    "text": {"content": line[cursor:start]}
                })
            # 数式部分
            equation_expr = match.group(1)
            rich_text.append({
                "type": "equation",
                "equation": {"expression": equation_expr}
            })
            cursor = end
        if cursor < len(line):
            # 残りのテキスト
            rich_text.append({
                "type": "text",
                "text": {"content": line[cursor:]}
            })

        return rich_text

    def create_child_page(self, parent_page_id: str, child_content: str):
        """
        指定した親ページに子ページを作成する。
        """
        child_page =  self.notion.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": "和訳全文",
                        },
                    }
                ]
            }
        )

        # 子ページにブロックを追加
        blocks = self.markdown_to_notion_blocks(child_content)
        for i in range(0, len(blocks), 100):
            self.notion.blocks.children.append(block_id=child_page["id"], children=blocks[i:i+100])
        return child_page

    def make_nest_page(self, child_page_content: str):
        assert self.untranslated_page is not None, "Untranslated page not loaded. Please run get_untranslated_page() first."
        # 未翻訳のページからIDを取得
        page_id = self.untranslated_page["id"]
        # 子ページを作成
        child_page = self.create_child_page(page_id,  child_page_content)
        print("Created child page with title")

    def input_translated_completed(self):
        """
        翻訳完了フラグを立てる。
        """
        assert self.untranslated_page is not None, "Untranslated page not loaded. Please run get_untranslated_page() first."
        self.notion.pages.update(
            page_id=self.untranslated_page["id"],
            properties={
                "Translate Completed": {
                    "checkbox": True
                }
            }
        )
