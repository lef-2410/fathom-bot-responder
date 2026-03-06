FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy email style guide (create yours from email-style.md.example)
COPY email-style.md /app/email-style.md

# Copy application code
COPY app/ /app/app/

CMD ["python", "-m", "app.main"]
