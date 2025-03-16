# ベースイメージを指定
FROM python:3.11-slim-bullseye
# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
# poetryの環境変数を設定
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
ENV PATH="${POETRY_HOME}/bin:${PATH}"
# poetryをインストール
RUN curl -sSL https://install.python-poetry.org | python - --version 1.8.3
# 作業ディレクトリを指定
WORKDIR /app
# プロジェクトの依存関係をインストール
COPY pyproject.toml poetry.lock ./ 
COPY app ./app
RUN poetry install --no-root
# ポートを指定
EXPOSE 3000
# アプリケーションを起動
CMD ["python", "app/main_for_cloud.py"]