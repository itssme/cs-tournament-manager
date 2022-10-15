FROM python:3.9

WORKDIR /

COPY requirements.txt requirements.txt

RUN apt install libpq-dev
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app app

WORKDIR app

EXPOSE 80 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
