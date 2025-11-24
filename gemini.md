# サポートAI「小夜」開発ドキュメント

## 概要
このドキュメントは、Gemini CLIを通じて行われた開発のタスク管理と進捗を記録します。

## [現タスク]
- [x] 現状のプロジェクト構造と実装状況の分析
- [x] `requirements.txt` の依存関係の精査
- [x] Whisperの動作確認
- [x] Gemini APIの単体動作確認
- [x] Whisper -> Gemini API連携テスト
- [x] VOICEVOX APIの単体動作確認
- [x] Whisperモデルのアップグレード (small -> medium)
- [ ] `sayo_core_voice.py` のリファクタリング（CLIプロトタイプの安定化）
    - [x] 起動ホットワードの追加（さよち）
    - [x] テキスト/音声による終了機能の実装
    - [x] リアルタイム処理ログの改善
    - [ ] （継続）高度な音声処理、クラス化、設定の外部化など
- [ ] ユニットテストの実装

## [残タスク]
- [ ] FastAPI + Vue.js への移行
- [ ] 詳細なエラーハンドリングの実装
- [ ] 永続的な会話履歴の管理機能

## プロジェクト構造
```
~~~/programs/personal/sayo_project/Sayo_smart_AI/
├── .gitignore
├── README.md
├── gemini.md  (このファイル)
└── backend/
    ├── .env (機密情報：Git管理対象外)
    ├── requirements.txt
    ├── sayo_core_voice.py
    ├── sayo_core_text.py
    ├── sayo_log.db (実行時に生成)
    └── venv/
```

## 実装状況サマリー

### `sayo_core_voice.py` (音声対話版)
CLIプロトタイプとしての基本機能は一通り実装済みです。

- **実装済み機能**:
    - [x] 音声認識 (Whisper: smallモデル)
    - [x] 思考エンジン (Gemini: gemini-2.5-flash)
    - [x] 音声合成 (VOICEVOX)
    - [x] 音声入出力 (マイク/スピーカー)
    - [x] 時報機能 (毎時0分)
    - [x] 会話ログDB保存 (SQLite)

### `sayo_core_text.py` (テキスト対話版)
`sayo_core_voice.py`から音声認識機能を削除した軽量版。

- **実装済み機能**:
    - [x] テキスト入力による対話
    - [x] 思考エンジン (Gemini: gemini-2.5-flash)
    - [x] 音声合成・自動再生 (VOICEVOX)
    - [x] 会話ログDB保存 (SQLite)

- **課題・未実装 (共通)**:
    - [ ] コードが単一ファイルに集約されており、将来的な拡張性のためクラス化やモジュール分割を検討する必要がある。
    - [ ] テストコードが未実装。

### `requirements.txt`
- **リストされているライブラリ**:
    - `openai-whisper`
    - `google-generativeai`
    - `requests`
    - `sounddevice`
    - `soundfile`
    - `schedule`
    - `numpy`
    - `setuptools`
    - `python-dotenv`
    - `importlib-metadata`

## 動作確認
- [x] Whisper (音声認識) - `ffmpeg`インストール後、正常に動作することを確認。
- [x] Gemini API (思考エンジン) - `gemini-2.5-flash`モデルで正常に動作することを確認。
- [x] Whisper -> Gemini API連携 - 正常に動作することを確認。
- [x] VOICEVOX API (音声合成) - テキスト送信と音声再生が正常に動作することを確認。
