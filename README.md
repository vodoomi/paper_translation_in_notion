# paper_translation_in_notion

### Preprocess
1. Make Slack App with Socket Mode to use Slack API
2. Invite Slack Bot to the channel
    1. Open the channel
    2. Select ‘Open channel details’ from the three dots in the top right-hand corner
    3. Select ‘Add app’ in App in Integration
3. Make database in notion
4. Add automations that notify to Slack when adding pdf

### Usage
1. Make .env file owing environment varibales
```bash
touch .env
echo "SLACK_BOT_TOKEN=your slack bot token" >> .env
echo "SLACK_APP_TOKEN=your slack app token" >> .env
echo "NOTION_USER_ID=your notion user id in slack" >> .env
```

2. Install dependencies
```bash
poetry install
```

3. Run
```bash
cd app
poetry run python main.py
```

4. Add paper in Notion database

### Response
```Slack
Hey there @Notion! 
```