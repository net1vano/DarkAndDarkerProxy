FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY app.py .

# Открываем порты (документация)
# 8080 для HTTP (конфиг)
# 20000-20250 для игры
EXPOSE 8080
EXPOSE 20000-20250

# Запуск приложения
CMD ["python", "proxy.py"]