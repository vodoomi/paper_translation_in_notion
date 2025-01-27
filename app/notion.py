import os
import re

from dotenv import load_dotenv
from notion_client import Client


class NotionWriter:
    def __init__(self):
        load_dotenv()
        self.notion_api_token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.notion = Client(auth=self.notion_api_token)
        self.pages = None

    def get_pages_from_database(self):
        """
        データベース内のページ一覧を取得する。
        """
        response = self.notion.databases.query(self.database_id)
        self.pages = response.get("results", [])

    def find_page_by_title(self, pages, title):
        """
        指定したタイトルに一致するページを探す。
        """
        for page in pages:
            # ページのプロパティにあるタイトルを取得
            page_title = page["properties"]["タイトル"]["title"][0]["plain_text"]
            if page_title == title:
                return page
        return None
    
    def markdown_to_notion_blocks(self, markdown_text: str) -> list:
        """
        Markdown形式のテキストをNotionのブロック形式に変換する。
        """

        blocks = []

        inline_math_pattern = re.compile(r"\$(.+?)\$")
        block_math_flag = False
        for line in markdown_text.splitlines():
            line = line.strip()

            if not line:
                continue
            
            if line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]
                    }
                })
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]
                    }
                })
            elif line.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]
                    }
                })
            elif line.startswith("$$"):
                block_math_flag = not block_math_flag
            elif block_math_flag:
                blocks.append({
                    "object": "block",
                    "type": "equation",
                    "equation": {
                        "expression": line.strip()
                    }
                })
            elif line.startswith("- "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]
                    }
                })
            elif line.startswith("1. "):
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]
                    }
                })
            else:
                # インライン数式の処理
                rich_text = []
                cursor = 0
                for match in inline_math_pattern.finditer(line):
                    start, end = match.span()
                    # 数式以外のテキスト部分を追加
                    if start > cursor:
                        rich_text.append({"type": "text", "text": {"content": line[cursor:start]}})
                    # 数式部分を追加
                    rich_text.append({"type": "equation", "equation": {"expression": match.group(1)}})
                    cursor = end

                # 残りのテキスト部分を追加
                if cursor < len(line):
                    rich_text.append({"type": "text", "text": {"content": line[cursor:]}})
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": rich_text
                    }
                })

        return blocks

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
        self.notion.blocks.children.append(block_id=child_page["id"], children=blocks)
        return child_page

    def make_nest_page(self, target_page_title: str, child_page_content: str):
        assert self.pages is not None, "Pages not loaded. Please run get_pages_from_database() first."
        # タイトルに一致するページを検索
        target_page = self.find_page_by_title(self.pages, target_page_title)

        if target_page:
            print(f"Found target page")
            parent_page_id = target_page["id"]

            # 子ページを作成
            child_page = self.create_child_page(parent_page_id,  child_page_content)
            print("Created child page with title")
        else:
            print("Target page with title not found.")
