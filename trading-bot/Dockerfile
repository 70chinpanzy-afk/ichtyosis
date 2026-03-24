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
CMD ["python", "-u", "paper_trader.py", "--interval", "14400"]
