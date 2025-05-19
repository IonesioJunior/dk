# Syft Agent: Setup and Deployment Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Development Environment Setup](#development-environment-setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Deployment Options](#deployment-options)
   - [Docker Deployment](#docker-deployment)
   - [Kubernetes Deployment](#kubernetes-deployment)
   - [Cloud Deployment](#cloud-deployment)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Introduction

This guide provides comprehensive instructions for setting up, configuring, and deploying the Syft Agent. Whether you're developing locally or deploying to production, these steps will help you get the Syft Agent up and running effectively.

## Prerequisites

Before setting up Syft Agent, ensure you have the following:

- **Python**: Version 3.12 or higher
- **uv**: Python package manager and virtual environment tool
- **Git**: For version control and setup
- **pre-commit**: For code quality checks
- **ChromaDB**: For document vector storage (optional for development)

If you're planning to deploy in production, you'll also need:

- **Docker** (optional): For containerized deployment
- **Kubernetes** (optional): For orchestrated deployment
- **A domain name** (optional): For public-facing deployments

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/syft_agent.git
cd syft_agent
```

### 2. Create a Virtual Environment

Syft Agent uses uv for virtual environment management:

```bash
# Create virtual environment using uv with Python 3.12
uv venv -p 3.12

# Activate the environment (Linux/macOS)
source .venv/bin/activate

# Activate the environment (Windows)
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install the required packages
uv pip install -r requirements-dev.txt

# Set up pre-commit hooks for code quality
pre-commit install
```

### 4. Install Sentence Transformers (Optional)

If you plan to use advanced embedding features:

```bash
uv pip install sentence-transformers
```

## Configuration

Syft Agent can be configured through environment variables and configuration files.

### Environment Variables

- `SYFTBOX_ASSIGNED_PORT`: Port to run the application on (default: 8080)
- `SYFTBOX_DEBUG`: Set to "1" to enable debug mode
- `CHROMADB_HOST`: Hostname for remote ChromaDB server (optional)
- `CHROMADB_PORT`: Port for remote ChromaDB server (optional)
- `CHROMADB_PERSIST_DIR`: Directory for persisting ChromaDB data (optional)

Example configuration:

```bash
# .env file
SYFTBOX_ASSIGNED_PORT=9000
SYFTBOX_DEBUG=1
CHROMADB_PERSIST_DIR=./data/chromadb
```

## Running the Application

### Development Mode

For development with auto-reload:

```bash
uv run uvicorn app:syftbox.app --host 0.0.0.0 --port 8080 --reload
```

### Production Mode

For production (with multiple workers):

```bash
uv run uvicorn app:syftbox.app --host 0.0.0.0 --port 8080 --workers 4
```

### Custom Port

To run on a specific port:

```bash
SYFTBOX_ASSIGNED_PORT=9000 uv run uvicorn app:syftbox.app --host 0.0.0.0 --port 9000 --workers 1
```

### Using the `run.sh` Script

The repository includes a `run.sh` script for convenience:

```bash
# Make the script executable
chmod +x run.sh

# Run with default settings
./run.sh

# Run with custom port
SYFTBOX_ASSIGNED_PORT=9000 ./run.sh
```

## Testing

### Running Tests

Syft Agent has a comprehensive test suite using pytest:

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/modules/documents/test_crud.py

# Run specific test
pytest tests/modules/documents/test_crud.py::test_create_document
```

### Running Linters and Type Checkers

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run mypy type checking
mypy modules

# Run ruff linter
ruff check modules

# Run bandit security checks
bandit -r modules
```

## Deployment Options

### Docker Deployment

#### 1. Create a Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN uv pip install -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8080

# Set environment variables
ENV PYTHONPATH=/app
ENV SYFTBOX_ASSIGNED_PORT=8080

# Run the application
CMD ["uvicorn", "app:syftbox.app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 2. Build and Run the Docker Container

```bash
# Build the Docker image
docker build -t syft-agent:latest .

# Run the container
docker run -p 8080:8080 -d \
  -v $(pwd)/data:/app/data \
  --name syft-agent \
  syft-agent:latest
```

### Kubernetes Deployment

#### 1. Create Kubernetes Manifests

**Deployment Manifest** (`k8s/deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: syft-agent
  labels:
    app: syft-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: syft-agent
  template:
    metadata:
      labels:
        app: syft-agent
    spec:
      containers:
      - name: syft-agent
        image: syft-agent:latest
        ports:
        - containerPort: 8080
        env:
        - name: SYFTBOX_ASSIGNED_PORT
          value: "8080"
        - name: CHROMADB_PERSIST_DIR
          value: "/data/chromadb"
        volumeMounts:
        - name: data-volume
          mountPath: /data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: syft-agent-pvc
```

**Service Manifest** (`k8s/service.yaml`):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: syft-agent
spec:
  selector:
    app: syft-agent
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

**PersistentVolumeClaim Manifest** (`k8s/pvc.yaml`):

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: syft-agent-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

#### 2. Deploy to Kubernetes

```bash
# Apply the manifests
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify the deployment
kubectl get pods -l app=syft-agent
kubectl get services syft-agent
```

### Cloud Deployment

#### AWS Elastic Beanstalk

1. Create a `Procfile` in the project root:

```
web: uvicorn app:syftbox.app --host 0.0.0.0 --port $PORT
```

2. Create `.ebextensions/01_packages.config`:

```yaml
packages:
  yum:
    git: []
    python312-devel: []
```

3. Deploy using the EB CLI:

```bash
eb init -p python-3.12 syft-agent
eb create syft-agent-env
```

#### Google Cloud Run

1. Build and push your Docker image:

```bash
# Build the image
docker build -t gcr.io/your-project-id/syft-agent .

# Push to Google Container Registry
docker push gcr.io/your-project-id/syft-agent
```

2. Deploy to Cloud Run:

```bash
gcloud run deploy syft-agent \
  --image gcr.io/your-project-id/syft-agent \
  --platform managed \
  --allow-unauthenticated
```

## Monitoring and Maintenance

### Logging

Syft Agent logs to standard output by default. In production, consider using a logging service to collect and analyze logs:

- ELK Stack (Elasticsearch, Logstash, Kibana)
- Datadog
- Prometheus with Grafana

### Health Checks

Implement health checks to monitor the application:

```python
@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
```

### Backups

For production deployments, regularly back up the following:

1. **ChromaDB Data**: If using persistent storage
2. **Configuration Files**: Environment variables and settings
3. **Custom Code**: Any modifications to the base code

Example backup script:

```bash
#!/bin/bash
# backup.sh

# Set backup directory
BACKUP_DIR="/path/to/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup ChromaDB data
tar -czf $BACKUP_DIR/chromadb_data.tar.gz /data/chromadb

# Backup configuration
cp .env $BACKUP_DIR/

# Backup code
git archive --format=tar.gz -o $BACKUP_DIR/codebase.tar.gz HEAD

echo "Backup completed: $BACKUP_DIR"
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms**: Errors when running `uvicorn app:syftbox.app`

**Solutions**:
- Check if the virtual environment is activated
- Verify all dependencies are installed: `uv pip install -r requirements.txt`
- Check for syntax errors in the code
- Ensure the port is not already in use: `lsof -i :8080`

#### 2. ChromaDB Connection Issues

**Symptoms**: Errors related to ChromaDB or vector operations

**Solutions**:
- If using a remote ChromaDB server, check network connectivity
- Verify the ChromaDB host and port settings
- Ensure the persistent directory exists and is writable
- Check ChromaDB logs for internal errors

#### 3. Performance Issues

**Symptoms**: Slow response times, high resource usage

**Solutions**:
- Increase the number of workers: `--workers 4`
- Optimize database queries and vector operations
- Use profiling tools to identify bottlenecks
- Consider scaling horizontally with Kubernetes

### Getting Help

If you encounter issues not covered here:

1. Check the existing issues on GitHub
2. Join the community channels for help
3. Open a new issue with detailed information:
   - Expected vs. actual behavior
   - Error messages and logs
   - Environment details (OS, Python version, etc.)
   - Steps to reproduce the issue

---

This setup and deployment guide covers the essentials for getting Syft Agent running in various environments. For more detailed information on specific features, refer to the other documentation files in the `docs/` directory.