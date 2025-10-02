#!/bin/bash

cd "$(dirname "$0")"
BOT_NAME=$(basename "$(pwd)")
SESSION_NAME="$BOT_NAME"

if screen -list | grep -q "\\.${SESSION_NAME}"; then
  echo "🛑 Остановка screen-сессии $SESSION_NAME..."
  screen -S "$SESSION_NAME" -X quit
  echo "✅ $BOT_NAME остановлен."
else
  echo "⚠️ screen-сессия $SESSION_NAME не найдена."
fi
