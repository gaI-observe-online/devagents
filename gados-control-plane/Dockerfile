FROM python:3.11-slim

WORKDIR /app

# Minimal tools for healthchecks and debugging
RUN apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY gados-control-plane/requirements.txt /app/gados-control-plane/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy repo code
COPY . /app

# Ensure shared modules are importable
ENV PYTHONPATH=/app

# Install the control plane package
RUN pip install --no-cache-dir -e /app/gados-control-plane

EXPOSE 8000

CMD ["uvicorn","gados_control_plane.main:app","--host","0.0.0.0","--port","8000"]

