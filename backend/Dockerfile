# Stage 1: Build
FROM python:3.9-slim AS builder

WORKDIR /app
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install-deps && playwright install

# Stage 2: Deploy
FROM python:3.9-slim AS deploy

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY . /app

CMD ["python3", "main.py"]
