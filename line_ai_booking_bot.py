# main.py
from flask import Flask, request, abort
import os
import openai
import requests
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

@app.route("/", methods=['POST'])
def webhook():
    event = request.json['events'][0]
    if event['type'] == 'message':
        msg_type = event['message']['type']
        reply_token = event['replyToken']

        if msg_type == 'image':
            message_id = event['message']['id']
            headers = {
                "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
            }
            # Get image binary
            image_content = requests.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=headers).content
            # Send to OpenAI Vision API
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "この画像は飲食店の予約表です。何時に何席空いているか読み取ってください。"},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_content.decode('latin1')}}
                    ]}
                ],
                max_tokens=500
            )
            reply_text = response["choices"][0]["message"]["content"]
        else:
            reply_text = "画像を送ってください。"

        reply(reply_token, reply_text)
    return 'OK'

def reply(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [
            {"type": "text", "text": text}
        ]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

if __name__ == "__main__":
    app.run(debug=True)
