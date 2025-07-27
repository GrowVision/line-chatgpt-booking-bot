# main.py
from flask import Flask, request, abort
import os
import openai
import requests
import base64
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# ✅ Renderで登録した環境変数の読み取り
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
openai.api_key = OPENAI_API_KEY

@app.route("/", methods=['POST'])
def webhook():
    event = request.json['events'][0]
    if event['type'] == 'message':
        msg_type = event['message']['type']
        reply_token = event['replyToken']

        if msg_type == 'image':
            # ✅ 画像を取得してbase64変換
            message_id = event['message']['id']
            headers = {
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
            }
            image_binary = requests.get(
                f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                headers=headers
            ).content
            image_b64 = base64.b64encode(image_binary).decode("utf-8")

            # ✅ ChatGPT Visionへ画像解析リクエスト
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "この画像は飲食店の予約表です。何時に何席空いているか読み取ってください。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]}
                ],
                max_tokens=500
            )
            reply_text = response["choices"][0]["message"]["content"]
        elif msg_type == 'text':
            # ✅ テキストにもChatGPTで返答（オプション）
            user_message = event['message']['text']
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": user_message}
                ],
                max_tokens=200
            )
            reply_text = response["choices"][0]["message"]["content"]
        else:
            reply_text = "画像かテキストを送ってください。"

        reply(reply_token, reply_text)
    return 'OK'

def reply(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [
            {"type": "text", "text": text}
        ]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
