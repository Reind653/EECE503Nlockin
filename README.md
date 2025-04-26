# Lock-in Application

The Lock-in application is a microservices-based system designed to demonstrate and evaluate different LLM (Large Language Model) implementations. The system consists of multiple interconnected services that represent different aspects of LLM integration and evaluation.

## System Components

- **UI**: Web interface for interacting with the system
- **EEP1** : Coordinates evaluation and routes requests
- **IEP1**: Parser
- **IEP2**: Scheduler
- **IEP3**: Google Calendar
- **IEP4**: Chat Bot

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) (for Kubernetes deployment)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)
- PowerShell

### Environment Setup

Set the required API keys in your environment:

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
$env:ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Local Development

1. Start the application using Docker Compose:

```powershell
docker-compose up
```

2. Access the UI at http://localhost:5002

3. To run individual services during development:

```powershell
cd UI
python app.py

# Or for other services
cd IEP1
python app.py
```

## Monitoring with Prometheus and Grafana

The application includes monitoring capabilities using Prometheus and Grafana.

### Starting Monitoring Locally

1. Start the monitoring services:

```powershell
# Option 1: Using the provided script
.\start-monitoring.ps1

# Option 2: Using Docker Compose directly
docker-compose up -d prometheus grafana
```

2. Access the monitoring interfaces:
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (credentials: admin/admin)

### Setting Up Grafana Dashboards

1. Log in to Grafana at http://localhost:3000 with username `admin` and password `admin`
2. Go to Configuration > Data Sources
3. Add Prometheus as a data source:
   - URL: http://prometheus:9090
   - Access: Server (default)
4. Create a new dashboard:
   - Click "+ Create" and select "Dashboard"
   - Add a new panel
   - Select metrics from the available services (UI, IEP1-4, EEP1)
   - Example metrics:
     - `http_request_duration_seconds{job="iep1"}`
     - `http_requests_total{job="eep1"}`

### Available Metrics

All services expose Prometheus metrics at their `/metrics` endpoint:
- UI: http://localhost:5002/metrics
- EEP1: http://localhost:5000/metrics
- IEP1: http://localhost:5001/metrics
- IEP2: http://localhost:5004/metrics
- IEP3: http://localhost:5003/metrics
- IEP4: http://localhost:5005/metrics

## Running Tests

The Lock-in application includes tests for each component.

### Running Unit Tests

To run tests for individual components:

```powershell
# Navigate to the component directory
cd IEP1

# Install test dependencies
pip install -r requirements.txt
pip install pytest

# Run tests
pytest
```

### Running Integration Tests

Integration tests can be run against the deployed services:

```powershell
# Make sure all services are running
docker-compose up -d

# Run integration tests
cd tests
pytest test_integration.py
```

## Kubernetes Deployment

For deploying to Kubernetes, refer to the main Kubernetes deployment instructions in the kubernetes folder.

### Manual Kubernetes Deployment

1. Start Minikube:
   ```powershell
   minikube start --driver=docker
   ```

2. Configure Docker to use Minikube's daemon:
   ```powershell
   minikube -p minikube docker-env --shell powershell | Invoke-Expression
   ```

3. Build Docker images:
   ```powershell
   docker-compose build
   ```

4. Apply Kubernetes manifests:
   ```powershell
   kubectl apply -f kubernetes/manifests/
   ```

5. Access the UI service:
   ```powershell
   minikube service ui
   ```