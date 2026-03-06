FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the email style guide from parent project
COPY email-style.md /app/email-style.md

# Copy application code
COPY app/ /app/app/

CMD ["python", "-m", "app.main"]
