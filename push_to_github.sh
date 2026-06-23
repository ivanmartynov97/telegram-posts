#!/bin/bash
# Пушит новые посты из queue/ в GitHub.
# Запускается launchd каждое воскресенье в 21:30, после генерации постов.

cd ~/Claude/Projects/telegram

echo "$(date): Начинаю пуш в GitHub..." >> push.log

git add queue/
git diff --staged --quiet && echo "$(date): Нет новых постов" >> push.log && exit 0

git commit -m "Новые посты: $(date +'%d.%m.%Y')"
git push

echo "$(date): Пуш завершён" >> push.log
