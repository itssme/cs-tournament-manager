FROM tiangolo/meinheld-gunicorn-flask:python3.7

RUN pip install flask python-telegram-bot requests Flask-Limiter Flask-Caching Flask-Compress aiorcon tqdm

COPY /app /app
