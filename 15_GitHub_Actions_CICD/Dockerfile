FROM python:3.12-slim

WORKDIR /app
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PYTHONUNBUFFERED=1

COPY app/ ./app/

# don't run as root inside the container
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["python", "-m", "app.server"]
