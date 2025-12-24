# Multi-stage build for FastAPI backend
# Stage 1: Build stage
FROM python:3.11-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev postgresql-dev libffi-dev

# Copy requirements file
COPY requirements-prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements-prod.txt

# Stage 2: Runtime stage
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache postgresql-libs curl libffi

# Create non-root user
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Add local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
