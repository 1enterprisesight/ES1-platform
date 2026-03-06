FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY app/ app/

EXPOSE 8010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
