class CFG:
    mistral_model_name = "mistral-ocr-latest"
    model_name = 'gemini-2.0-flash'
    prompt = "以下のマークダウンファイルを翻訳してください。翻訳内容以外の文章は決して出力しないでください。数式と画像、テーブルは絶対に変更しないでください。インライン数式は$で、ブロック数式は$$で囲われています。画像は!で始まり、テーブルは'|'で囲われています。科学的専門用語は無理に訳さず英語表記でおねがいします。入力された文章を日本語で意訳しなさい。"
    output_dir = "../output/"
    gyazo_endpoint = "https://upload.gyazo.com/api/upload"
    max_input_words = 4096 # geminiの出力トークン数の上限が8192で、出力トークン数は入力単語数の約2倍になるため、入力単語数は4096以下にする
cfg = CFG()