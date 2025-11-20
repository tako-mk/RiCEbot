# ベース
FROM python:3.11-slim

# 作業ディレクトリ作成
WORKDIR /app

# 依存ファイルを先にコピー（キャッシュ効率良くするため）
COPY requirements.txt .

# 依存ライブラリのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー
COPY . .

# 起動コマンド
CMD ["python", "RiCEbot/bot.py"]
