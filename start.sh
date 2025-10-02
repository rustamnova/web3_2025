#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

BOT_NAME=$(basename "$(pwd)")
LOG_DIR="logs"
STDOUT_LOG="$LOG_DIR/run.log"
STDERR_LOG="$LOG_DIR/error.log"

mkdir -p "$LOG_DIR"
touch "$STDOUT_LOG" "$STDERR_LOG"

echo "[ $(date) ] ▶️ Запуск бота $BOT_NAME..." >> "$STDOUT_LOG"
exec python "$BOT_NAME.py" >> "$STDOUT_LOG" 2>> "$STDERR_LOG"
