FROM python:3.11-slim

WORKDIR /app

# Backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend
COPY app.py .
COPY pages/ ./pages/

# Expose ports
EXPOSE 8000 8501

# Start both services
CMD ["sh", "-c", "python backend/main.py & python -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0"]
