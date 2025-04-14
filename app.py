
from flask import Flask, request, abort
import os
import yaml
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.models import QuickReply, QuickReplyItem, MessageAction

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_SECRET")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

with open("stage_based_scripts.yaml", encoding="utf-8") as f:
    stages = yaml.safe_load(f)

user_stage = {}

def get_stage(stage_name):
    for stage in stages:
        if stage['stage'] == stage_name:
            return stage
    return None

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent)
def handle_message(event):
    if not isinstance(event.message, TextMessageContent):
        return

    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    if user_msg == "重來":
        user_stage[user_id] = "進入情境"

    current_stage_name = user_stage.get(user_id, "進入情境")
    current = get_stage(current_stage_name)
    user_stage[user_id] = current_stage_name

    messages = []

    if 'options' in current:
        for option in current['options']:
            if user_msg == option['label']:
                next_stage = get_stage(option['next_stage'])
                user_stage[user_id] = option['next_stage']
                if 'reply' in next_stage:
                    messages.append(TextMessage(text=next_stage['reply']))
                elif 'prompt' in next_stage and 'options' in next_stage:
                    quick_reply = QuickReply(items=[
                        QuickReplyItem(action=MessageAction(label=opt['label'], text=opt['label']))
                        for opt in next_stage['options']
                    ])
                    messages.append(TextMessage(text=next_stage['prompt'], quick_reply=quick_reply))
                break

    if not messages:
        if 'prompt' in current and 'options' in current:
            quick_reply = QuickReply(items=[
                QuickReplyItem(action=MessageAction(label=opt['label'], text=opt['label']))
                for opt in current['options']
            ])
            messages.append(TextMessage(text=current['prompt'], quick_reply=quick_reply))
        else:
            messages.append(TextMessage(text="請選擇下方的選項繼續對話，或輸入「重來」重新開始。"))

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
