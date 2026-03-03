# ─────────────────────────────────────────────────────────────
# GOVINDA v8 — Docker Image
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Raghav"
LABEL version="8.0"
LABEL description="GOVINDA NIFTY AI Trading System"

# IST timezone
ENV TZ=Asia/Kolkata
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tzdata curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/govinda

# Install deps (cached layer)
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ .

# Runtime directories
RUN mkdir -p data logs saved_models mlruns

# Non-root user
RUN useradd -m -u 1000 govinda && chown -R govinda:govinda /opt/govinda
USER govinda

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "from utils.lot_sizes import get_lot_size; assert get_lot_size('NIFTY')==65"

EXPOSE 8501

CMD ["python", "main.py"]
