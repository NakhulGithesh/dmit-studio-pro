FROM python:3.11-slim

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies: headless LibreOffice, DejaVu fonts, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-nogui \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose standard Streamlit port
EXPOSE 8501

# Run Streamlit securely bound to 0.0.0.0
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
