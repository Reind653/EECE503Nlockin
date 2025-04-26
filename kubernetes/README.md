# Kubernetes Deployment for Lock-in Application

This directory contains all the necessary files to deploy the Lock-in application on Kubernetes using Minikube.

## Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/docs/start/) (v1.20.0+)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) (v1.20.0+)
- [Docker](https://docs.docker.com/get-docker/) (required for Minikube)
- PowerShell (for running the provided scripts)

## Directory Structure

- `manifests/`: Contains Kubernetes manifest files for all services
  - `api-keys-secret.yaml`: Secret for API keys
  - `iep1-deployment.yaml`: IEP1 service deployment and service
  - `iep2-deployment.yaml`: IEP2 service deployment and service
  - `iep3-deployment.yaml`: IEP3 service deployment and service
  - `iep4-deployment.yaml`: IEP4 service deployment and service
  - `eep1-deployment.yaml`: EEP1 service deployment and service
  - `ui-deployment.yaml`: UI service deployment and service
  - `ingress.yaml`: Ingress resource for external access
- `deploy.ps1`: Main deployment script
- `update-api-keys.ps1`: Script to update API keys in the secret file
- `cleanup.ps1`: Script to clean up deployed resources

## Deployment Steps

### 1. Update API Keys

Before deployment, update your API keys in the yaml file:
cd kubernetes\manifests
Go to api-keys-secret.yaml
Update values of "your-openai-key" and  "your-anthropic-key"

Before deployment, update your API keys in the script:

```powershell
cd kubernetes
.\update-api-keys.ps1 -OpenAIKey "your-openai-key" -AnthropicKey "your-anthropic-key"
```

### 2. Deploy the Application

Run the deployment script:

```powershell
cd kubernetes
.\deploy.ps1
```

This script will:
- Start Minikube if not already running
- Configure Docker to use Minikube's daemon
- Build all required Docker images
- Apply all Kubernetes manifests
- Enable the Ingress addon for external access
- Wait for all services to be ready
- Print access information

### 3. Access the Application

After successful deployment, access the UI service:

```powershell
minikube service ui
```

### 4. Cleanup

To remove the deployed application:

```powershell
cd kubernetes
.\cleanup.ps1
```

## Manual Deployment

If you prefer to deploy manually:

1. Start Minikube:
   ```
   minikube start --driver=docker
   ```

2. Configure Docker to use Minikube's daemon:
   ```
   minikube -p minikube docker-env --shell powershell | Invoke-Expression
   ```

3. Build Docker images:
   ```
   cd ..
   docker-compose build
   ```

4. Apply Kubernetes manifests:
   ```
   cd kubernetes
   kubectl apply -f manifests/
   ```

5. Enable Ingress addon (optional):
   ```
   minikube addons enable ingress
   ```

## Troubleshooting

- **Pod in CrashLoopBackOff**: Check the logs with `kubectl logs <pod-name>`
- **Service not accessible**: Verify service with `kubectl get svc` and make sure the service type is correctly set
- **API keys not working**: Update the API keys and redeploy the secret with `kubectl apply -f manifests/api-keys-secret.yaml`

## Additional Commands

- Get all resources: `kubectl get all`
- Get detailed info on a pod: `kubectl describe pod <pod-name>`
- Get logs from a container: `kubectl logs <pod-name>`
- Get a shell in a container: `kubectl exec -it <pod-name> -- /bin/sh`
- Delete all resources: `kubectl delete -f manifests/` 