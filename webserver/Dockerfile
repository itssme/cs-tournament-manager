FROM python:3.11 AS builder

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt install libpq-dev nodejs -y

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade --user -r requirements.txt

WORKDIR /app/static
RUN npm install -D tailwindcss tw-elements

COPY ./static/css /app/static/css
COPY ./static/tailwind.config.js /app/static/tailwind.config.js
COPY ./templates /app/templates
RUN npx tailwindcss -c /app/static/tailwind.config.js -i /app/static/css/input.css -o /app/static/css/output.css

FROM python:3.11-slim

RUN apt-get update && apt-get install libpq-dev -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/static/css /app/static/css
COPY --from=builder /app/static/node_modules/tw-elements /app/static/node_modules/tw-elements
ENV PATH=/root/.local/bin:$PATH
ENV GUNICORN_CMD_ARGS=--preload

COPY . .

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]