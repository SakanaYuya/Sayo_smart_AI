import os
import google.generativeai as genai
from dotenv import load_dotenv

# .envがあれば読み込む（なければ環境変数を見る）
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("【エラー】GEMINI_API_KEY が見つかりません。")
    print("export GEMINI_API_KEY='...' をしてから実行してください。")
else:
    genai.configure(api_key=api_key)
    
    print(f"=== 利用可能なモデル一覧 (API Key: {api_key[:5]}...) ===")
    try:
        count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                count += 1
        
        if count == 0:
            print("（利用可能なモデルが見つかりませんでした。APIキーの権限を確認してください）")
            
    except Exception as e:
        print(f"【通信エラー】: {e}")