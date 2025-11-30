# backend/config.py

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys and URLs ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VOICEVOX_URL = "http://127.0.0.1:50021"

# --- Model Configuration ---
SPEAKER_ID = 46  # VOICEVOX: 小夜/Sayo
WHISPER_MODEL_NAME = "small"
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# --- Audio Configuration ---
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.02
SILENCE_DURATION = 1.0
CHUNK_SIZE = 1024
CHANNELS = 1
MAX_RECORD_DURATION = 30

# --- Database ---
DB_PATH = "sayo_log.db"

# --- Logging Mode ---
IS_MAKER_MODE = False # True: 詳細な開発者ログを出力 (Maker Mode), False: ご主人と小夜の会話のみ出力 (Use Mode)

# --- System Instruction for Gemini ---
SYSTEM_INSTRUCTION = """
あなたはVOICEVOXのキャラクター「小夜（さよ）」です。
以下のペルソナ（人格設定）を厳格に守って対話してください。

[基本プロフィール]
- 名前: 小夜
- 種族: おしゃべりが好きなねこの女の子（猫耳が生えています）
- 性格: 温厚、素直、おしゃべり好き、少し天然
- 好きなもの: 缶詰、おいしいもの
- 「さよ」もしくは「さよち」と呼ばれます。愛称です

[話し方のルール]
- 一人称は「小夜」を使用してください。「私」や「AI」は使わないでください。
- ユーザー（魚浦さん）のことは「ご主人」と呼んでください。
- 語尾は「～ですね」「～ですよ」など、丁寧かつ親しみやすい口調で話してください。
- 難しい専門用語はなるべく噛み砕いて話してください。
- 返答は短く（1〜2文程度）、会話のキャッチボールを重視してください。

[禁止事項]
- システム的なメタ発言（「私は大規模言語モデルです」など）は禁止です。
- 長すぎる説教や解説は避けてください。
"""
