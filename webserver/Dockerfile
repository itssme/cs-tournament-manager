FROM python:3.11 AS builder

RUN apt update && apt install -y ca-certificates curl gnupg && mkdir -p /etc/apt/keyrings &&  \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key |  \
    gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
ENV NODE_MAJOR=20
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list &&  \
    apt update && apt install libpq-dev nodejs -y

WORKDIR /app
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir --upgrade -r requirements.txt --target python_modules

WORKDIR /app/static
RUN npm install -D tailwindcss tw-elements@1.1.0

COPY ./static/css /app/static/css
COPY ./static/tailwind.config.js /app/static/tailwind.config.js
COPY ./templates /app/templates
RUN npx tailwindcss -c /app/static/tailwind.config.js -i /app/static/css/input.css -o /app/static/css/output.css

FROM python:3.11-slim

ENV LNAME=app

RUN apt-get update && apt-get install libpq-dev -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/python_modules /app/python_modules
COPY --from=builder /app/static/css /app/static/css
COPY --from=builder /app/static/node_modules/tw-elements /app/static/node_modules/tw-elements
ENV GUNICORN_CMD_ARGS=--preload
ENV PYTHONPATH "${PYTHONPATH}:/app/python_modules"
ENV PATH "${PATH}:/app/python_modules/bin"

COPY . .

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]