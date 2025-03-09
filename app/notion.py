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
        Markdown形式のテキストをNotionのブロック形式に変換する。
        """

        blocks = []

        inline_math_pattern = re.compile(r"\$(.+?)\$")
        block_math_flag = False
        for text_split in markdown_text.splitlines():
            for i in range(0, len(text_split), chunk_size):
                line = text_split[i:i+chunk_size]
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
                elif line.startswith("https://") and line.endswith(".jpg"):
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
