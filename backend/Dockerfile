FROM python:3.11-slim

WORKDIR /app

# Install dependencies using pip and pyproject.toml
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

# Copy application code
COPY app /app/app

# Expose port (Cloud Run sets PORT env var)
ENV PORT=8080
EXPOSE ${PORT}

# Run FastAPI server
# Cloud Run injects the PORT environment variable (default 8080)
# We must use shell form to evaluate the $PORT variable correctly
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
