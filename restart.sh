#!/bin/bash

cd "$(dirname "$0")"
BOT_NAME=$(basename "$(pwd)")
SESSION_NAME="$BOT_NAME"

if screen -list | grep -q "\\.${SESSION_NAME}"; then
  echo "🛑 Остановка screen-сессии $SESSION_NAME..."
  screen -S "$SESSION_NAME" -X quit
fi

echo "🔄 Перезапуск $BOT_NAME..."
screen -dmS "$SESSION_NAME" ./start.sh

echo "✅ $BOT_NAME перезапущен в screen: $SESSION_NAME"
