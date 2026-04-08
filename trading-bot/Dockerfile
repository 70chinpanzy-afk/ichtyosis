FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY *.py .

# Create directories for data persistence
RUN mkdir -p charts results

# Run paper trader
CMD ["python", "-u", "bot_v2.py", "--interval", "3600"]
