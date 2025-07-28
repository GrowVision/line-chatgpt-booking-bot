# main.py
from flask import Flask, request, abort
import os
import requests
import base64
import threading
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__)
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

client = OpenAI(api_key=OPENAI_API_KEY)

# デバッグ用: 環境変数が読み込まれているか確認
print("✅ OPENAI_API_KEY:", OPENAI_API_KEY[:8] if OPENAI_API_KEY else "None")
print("✅ LINE_CHANNEL_SECRET:", LINE_CHANNEL_SECRET[:8] if LINE_CHANNEL_SECRET else "None")
print("✅ LINE_CHANNEL_ACCESS_TOKEN:", LINE_CHANNEL_ACCESS_TOKEN[:8] if LINE_CHANNEL_ACCESS_TOKEN else "None")

@app.route("/", methods=['GET', 'HEAD', 'POST'])
def webhook():
    if request.method == 'GET' or request.method == 'HEAD':
        return "OK", 200  # LINE Verify用のGET/HEAD対応

    try:
        body = request.get_json()
        print("📩 受信したリクエスト:", body)

        if 'events' not in body or len(body['events']) == 0:
            print("[⚠️ イベントなし] 'events' キーが見つかりません")
            return "No events", 200

        threading.Thread(target=handle_event, args=(body,)).start()
        return "OK", 200

    except Exception as e:
        print("[❌ webhookエラー]", e)
        return "Internal Server Error", 500

def handle_event(body):
    try:
        print("✅ handle_event 呼び出し成功:", body)
        event = body['events'][0]
        print("✅ event:", event)

        if event['type'] == 'message':
            msg_type = event['message']['type']
            reply_token = event['replyToken']
            print("✅ message type:", msg_type)

            if msg_type == 'image':
                print("✅ 画像処理開始")
                message_id = event['message']['id']
                headers = {
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
                }
                image_binary = requests.get(f"https://api-data.line.me/v2/bot/message/{message_id}/content", headers=headers).content
                image_b64 = base64.b64encode(image_binary).decode("utf-8")
                response = client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "この画像は飲食店の予約表です。何時に何席空いているか読み取ってください。"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                            ]
                        }
                    ],
                    max_tokens=500
                )
                reply_text = response.choices[0].message.content
            elif msg_type == 'text':
                reply_text = "画像を送ると、AIが予約状況を読み取ってお返事します！"
            else:
                reply_text = "画像を送ってください。"

            print("✅ 返信内容:", reply_text)
            reply(reply_token, reply_text)
    except Exception as e:
        print("[❌ handle_eventエラー]", e)

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
