FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

WORKDIR /

COPY requirements.txt requirements.txt

RUN apt update && apt install libpq-dev npm -y
RUN pip install --no-cache-dir --upgrade -r requirements.txt

WORKDIR /app/static
RUN npm install -D tailwindcss
RUN npx tailwindcss init
RUN npm install tw-elements
WORKDIR /

COPY . app

WORKDIR /app/static/

RUN npx tailwindcss -i /app/static/css/input.css -o /app/static/css/output.css

WORKDIR /app

EXPOSE 80 80
