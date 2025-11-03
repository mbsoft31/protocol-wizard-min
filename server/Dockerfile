# Multi-stage build for Protocol Wizard API

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install LLM providers (optional)
ARG INSTALL_OPENAI=true
ARG INSTALL_GEMINI=true

RUN if [ "$INSTALL_OPENAI" = "true" ]; then \
        pip install --no-cache-dir openai>=1.47; \
    fi && \
    if [ "$INSTALL_GEMINI" = "true" ]; then \
        pip install --no-cache-dir google-generativeai>=0.7; \
    fi

# Stage 2: Runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser server/ ./server/
COPY --chown=appuser:appuser prompts/ ./prompts/
COPY --chown=appuser:appuser schemas/ ./schemas/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
