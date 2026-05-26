FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        libffi8 \
        libgdk-pixbuf-2.0-0 \
        libharfbuzz-subset0 \
        libharfbuzz0b \
        libjpeg62-turbo \
        libopenjp2-7 \
        nodejs \
        npm \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN npm --prefix /app/parser-core ci \
    && npm --prefix /app/parser-core run build

EXPOSE 8080

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
