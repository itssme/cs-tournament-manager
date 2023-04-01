FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

WORKDIR /

COPY requirements.txt requirements.txt

RUN apt update && apt install libpq-dev -y
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . app

WORKDIR /app

EXPOSE 80 80
