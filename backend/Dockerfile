FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/

WORKDIR /app/backend

ENV PYTHONPATH=/app/backend

RUN groupadd --system agro && useradd --system --gid agro --home-dir /app agro \
    && chown -R agro:agro /app

USER agro

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
