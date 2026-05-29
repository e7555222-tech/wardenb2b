# Tek konteyner yerel geliştirme için (üretim: docker-compose.yml)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY app.py config.py ./
COPY pages/ ./pages/
COPY .streamlit/ ./.streamlit/

ENV API_URL=http://localhost:8000

EXPOSE 8000 8501

CMD ["sh", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run /app/app.py --server.port=8501 --server.address=0.0.0.0"]
