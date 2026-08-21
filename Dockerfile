FROM python:3.11-slim
WORKDIR /app
COPY bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY bot /app/bot
CMD ["python", "-u", "bot/main.py"]
