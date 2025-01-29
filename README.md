# Paper Translation in Notion

### Preprocess
1. Make Slack App with Socket Mode to use Slack API
2. Invite Slack Bot to the channel
    1. Open the channel
    2. Select ‘Open channel details’ from the three dots in the top right-hand corner
    3. Select ‘Add app’ in App in Integration
3. Make database in notion
4. Add automations that notify to Slack when adding pdf
5. Make integration to use Notion API (https://www.notion.so/my-integrations)
6. Connect integration on the page you want to operate
7. Get internal integration secret and database ID

### Usage
1. Make .env file owing environment varibales
```bash
touch .env
echo "SLACK_BOT_TOKEN=your slack bot token" >> .env
echo "SLACK_APP_TOKEN=your slack app token" >> .env
echo "NOTION_USER_ID=your notion user id in slack" >> .env
echo "GEMINI_API_KEY=your gemini api key" >> .env
echo "NOTION_TOKEN=your internal integration secret" >> .env
echo "NOTION_DATABASE_ID=your notion database id" >> .env
echo "GYAZO_ACCESS_TOKEN=your gyazo access token" >> .env
```

2. Install dependencies
```bash
poetry install
```

3. Modify module names in import and arg name
```bash
sed -i 's/from rapidocr_onnxruntime.ch_ppocr_rec.text_recognize/from rapidocr_onnxruntime.ch_ppocr_v3_rec.text_recognize/' .venv/Lib/site-packages/cnocr/ppocr/rapid_recognizer.py
sed -i 's/from rapidocr_onnxruntime.ch_ppocr_det/from rapidocr_onnxruntime.ch_ppocr_v3_det/' .venv/Lib/site-packages/cnstd/ppocr/rapid_detector.py
sed -i 's/fitz.open(pdf_fp/fitz.open(stream=pdf_fp/' .venv/Lib/site-packages/pix2text/pix_to_text.py
```

4. Run
```bash
cd app
poetry run python main.py
```

5. Add paper in Notion database

### Response
Generate translations on Notion child pages.

### Demo
https://github.com/user-attachments/assets/d98a16f9-d92b-4cd1-a036-9e868935f1af

### Reference
- Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. arXiv preprint arXiv:2203.05794.
