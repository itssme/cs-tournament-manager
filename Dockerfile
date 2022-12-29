FROM python:3.9

WORKDIR /

RUN wget "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.2.4/tailwindcss-linux-x64"
RUN mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss && chmod +x /usr/local/bin/tailwindcss

COPY requirements.txt requirements.txt

RUN apt install libpq-dev
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app app

WORKDIR app

RUN tailwindcss init
RUN echo "module.exports = { content: ['./templates/**/*.html'], darkMode: false, theme: { extend: {}, }, variants: { extend: {}, }, plugins: [], }" > tailwind.config.js
RUN tailwindcss -i ./static/css/input.css -o ./static/css/output.css

EXPOSE 80 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
