FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --system metro && useradd --system --gid metro --home-dir /app metro
COPY cloud/requirements.txt /app/cloud/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: -r /app/cloud/requirements.txt
COPY cloud/ /app/cloud/
COPY web-staging/ /app/web-staging/
USER metro
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn cloud.pilot:app --host 0.0.0.0 --port ${PORT:-8080}"]
