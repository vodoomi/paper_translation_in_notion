class CFG:
    model_name = 'gemini-1.5-flash'
    prompt = "あなたは翻訳ツールです。翻訳内容以外の文章は決して出力しないでください。数式は絶対に変更しないでください。インライン数式は$で、ブロック数式は$$で囲われています。科学的専門用語は無理に訳さず英語表記でおねがいします。入力された文章を日本語で意訳しなさい。"
    output_dir = "../output/"
    gyazo_endpoint = "https://upload.gyazo.com/api/upload"
cfg = CFG()