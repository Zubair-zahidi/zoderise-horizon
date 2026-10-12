FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 zoderise && useradd --uid 10001 --gid zoderise --create-home zoderise
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY --chown=zoderise:zoderise . .
RUN mkdir -p /app/data/storage && chown -R zoderise:zoderise /app/data
USER zoderise
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.fileWatcherType=none"]
