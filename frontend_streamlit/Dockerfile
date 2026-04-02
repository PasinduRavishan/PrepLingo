FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and Streamlit config
COPY app.py .
COPY .streamlit/ ./.streamlit/

# Expose Streamlit port
EXPOSE 8501

# BACKEND_URL is injected by docker-compose — points to backend container on internal network
# Streamlit config: headless=true is already set in config.toml
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
