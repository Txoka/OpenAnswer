# Stage 1: Build
FROM python:3.9-slim AS deploy

WORKDIR /app
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install-deps && playwright install

COPY . /app

CMD ["python3", "main.py"]
