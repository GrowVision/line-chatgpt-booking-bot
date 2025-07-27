# main.py
from flask import Flask, request, abort
import os
import openai
import requests
import base64
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
openai.api_key = OPENAI_API_KEY

# デバッグ用: 環境変数が読み込まれているか確認
print("✅ OPENAI_API_KEY:", OPENAI_API_KEY[:8] if OPENAI_API_KEY else "None")
print("✅ LINE_CHANNEL_SECRET:", LINE_CHANNEL_SECRET[:8] if LINE_CHANNEL_SECRET else "None")
print("✅ LINE_CHANNEL_ACCESS_TOKEN:", LINE_CHANNEL_ACCESS_TOKEN[:8] if LINE_CHANNEL_ACCESS_TOKEN else "None")

@app.route("/", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK", 200  # LINE Verify用のGETリクエスト対応

    try:
        body = request.get_json()
        print("📩 受信したリクエスト:", body)

        event = body['events'][0]
        if event['type'] == 'message':
            msg_type = event['message']['type']
            reply_token = event['replyToken']

            if msg_type == 'image':
                message_id = event['message']['id']
                headers = {
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
                }
                image_binary = requests.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=headers).content
                image_b64 = base64.b64encode(image_binary).decode("utf-8")
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
                reply_text = "画像を送ると、AIが予約状況を読み取ってお返事します！"
            else:
                reply_text = "画像を送ってください。"

            reply(reply_token, reply_text)
    except Exception as e:
        print("[❌ エラー]", e)
        return "Internal Server Error", 500

    return 'OK', 200

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
    res = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=body)
    print("📨 LINE返信ステータス:", res.status_code)
    print("📨 LINE返信レスポンス:", res.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
