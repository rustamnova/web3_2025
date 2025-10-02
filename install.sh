#!/bin/bash

echo "🚀 Универсальная установка Telegram-бота..."

WORKDIR="/root/.bots"
mkdir -p "$WORKDIR"

# === Шаг 1: Получение .env ===
echo "📥 Вставьте .env файл (GITHUB_TOKEN, BOT_TOKEN, OPENAI_API_KEY, REPO_URL), затем нажмите Ctrl+D:"
ENV_TEMP=$(mktemp)
cat > "$ENV_TEMP"
source "$ENV_TEMP"

# === Проверка переменных ===
if [[ -z "$GITHUB_TOKEN" || -z "$BOT_TOKEN" || -z "$REPO_URL" ]]; then
  echo "❌ Не заданы GITHUB_TOKEN, BOT_TOKEN или REPO_URL"
  exit 1
fi

# === Шаг 2: Клонирование репозитория ===
REPO=$(echo "$REPO_URL" | sed -E 's|https://github.com/||;s|\.git$||')
BOT_NAME=$(basename "$REPO")
BOT_DIR="$WORKDIR/$BOT_NAME"

echo "🌐 Клонируем репозиторий $REPO_URL → $BOT_DIR"
rm -rf "$BOT_DIR"
git clone https://$GITHUB_TOKEN@github.com/$REPO.git "$BOT_DIR" || {
  echo "❌ Ошибка клонирования"
  exit 1
}

# === Копирование .env ===
cp "$ENV_TEMP" "$BOT_DIR/.env"
rm "$ENV_TEMP"

# === Переход в директорию и проверка основного .py файла ===
cd "$BOT_DIR" || exit 1
if [ ! -f "$BOT_NAME.py" ]; then
  echo "❌ Не найден файл $BOT_NAME.py"
  exit 1
fi

# === Установка системных пакетов ===
echo "📦 Установка зависимостей..."
apt update
apt install -y python3.12 python3.12-venv python3.12-dev git screen ffmpeg build-essential

# === Виртуальное окружение ===
echo "🐍 Настройка Python-окружения..."
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || true

# === Генерация start.sh ===
echo "⚙️ Генерация start.sh..."
cat <<EOF > start.sh
#!/bin/bash
cd "\$(dirname "\$0")"
source venv/bin/activate
touch log.txt error.log
echo "[\$(date)] ▶️ Запуск $BOT_NAME..." >> log.txt
python $BOT_NAME.py >> log.txt 2>> error.log
EOF

chmod +x start.sh

# === Завершение старых screen-сессий ===
echo "🧹 Завершаем старые screen-сессии: $BOT_NAME"
screen -ls | grep "\.${BOT_NAME}" | awk '{print $1}' | while read -r session_id; do
  screen -S "$session_id" -X quit
done

# === Запуск новой screen-сессии ===
echo "📺 Запуск новой screen-сессии..."
screen -dmS "$BOT_NAME" "$BOT_DIR/start.sh"

sleep 1
if screen -list | grep -q "\.${BOT_NAME}"; then
  echo "✅ Бот $BOT_NAME запущен в screen-сессии"
else
  echo "❌ Ошибка запуска screen-сессии"
fi

echo "ℹ️ Подключиться: screen -r $BOT_NAME"
