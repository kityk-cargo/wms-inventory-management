# Stage 1: Build dependencies
FROM python:3.9-slim as builder

WORKDIR /install
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final image
FROM python:3.9-slim

WORKDIR /app
# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy only the production code (e.g. the app folder)
COPY app/ ./app/

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
