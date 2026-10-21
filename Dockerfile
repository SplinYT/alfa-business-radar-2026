FROM python:3.12.8-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DB_PATH=/state/radar.sqlite
COPY app /app/app
COPY web /app/web
COPY data/demo /app/data/demo
COPY scripts /app/scripts
RUN useradd --uid 10001 --create-home radar && mkdir /state && chown radar:radar /state
USER radar
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"
CMD ["python", "-m", "app.server"]
