from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from linebot.exceptions import InvalidSignatureError
import os
import yaml

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
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
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text

    if user_id not in user_stage:
        current = get_stage("進入情境")
        user_stage[user_id] = "進入情境"
    else:
        current = get_stage(user_stage[user_id])

    if 'options' in current:
        for option in current['options']:
            if user_msg.strip() == option['label']:
                next_stage = get_stage(option['next_stage'])
                user_stage[user_id] = option['next_stage']
                if 'reply' in next_stage:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=next_stage['reply'])
                    )
                elif 'prompt' in next_stage and 'options' in next_stage:
                    quick = QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label=opt['label'], text=opt['label']))
                        for opt in next_stage['options']
                    ])
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=next_stage['prompt'], quick_reply=quick)
                    )
                return

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇下方的選項繼續對話。")
        )
        return

    if 'prompt' in current and 'options' in current:
        quick = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label=opt['label'], text=opt['label']))
            for opt in current['options']
        ])
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=current['prompt'], quick_reply=quick)
        )
