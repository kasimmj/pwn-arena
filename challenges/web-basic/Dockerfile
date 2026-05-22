FROM python:3.12-slim

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

ENV FLAG=placeholder
ENV PORT=80

EXPOSE 80
CMD ["python", "app.py"]
