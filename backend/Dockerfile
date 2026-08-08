FROM python:3.12.13-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall --yes setuptools pip \
    && addgroup --system marketlens \
    && adduser --system --ingroup marketlens --home /app marketlens

COPY --chown=marketlens:marketlens app ./app

RUN mkdir -p /app/data && chown -R marketlens:marketlens /app/data

USER marketlens

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
