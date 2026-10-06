# alpine instead of slim: the slim (Debian) base had 44 HIGH CVEs with no fix available, alpine has none
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# run as an unprivileged user, not root
RUN adduser -D -u 10001 appuser
USER 10001

EXPOSE 5001
# a production WSGI server instead of Flask's development server
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--access-logfile", "-", "app.app:app"]
