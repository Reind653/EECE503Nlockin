Write-Host "Starting Minikube deployment for Lock-in application..."

# Check if Minikube is installed
if (!(Get-Command minikube -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Minikube is not installed! Please install it first."
    exit 1
}

# Check if kubectl is installed
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl is not installed! Please install it first."
    exit 1
}

# 1. Start Minikube if not already running
$minikubeStatus = minikube status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Starting Minikube..."
    minikube start --driver=docker
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to start Minikube!"
        exit 1
    }
}
else {
    Write-Host "Minikube is already running."
}

# 2. Configure Docker to use Minikube's daemon
Write-Host "Configuring Docker to use Minikube's daemon..."
minikube -p minikube docker-env --shell powershell | Invoke-Expression

# 3. Build the Docker images
Write-Host "Building Docker images..."
# Navigate to the project root directory
Set-Location ..
docker-compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to build Docker images!"
    exit 1
}

# 4. Check if API keys are set
$secretFile = "kubernetes/manifests/api-keys-secret.yaml"
$secretContent = Get-Content -Path $secretFile -Raw
if ($secretContent -match '"YOUR_OPENAI_API_KEY"' -or $secretContent -match '"YOUR_ANTHROPIC_API_KEY"') {
    Write-Host "WARNING: API keys in $secretFile have not been updated!"
    Write-Host "Please run update-api-keys.ps1 with your actual API keys before continuing."
    
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Deployment canceled."
        exit 0
    }
}

# 5. Apply Kubernetes manifests
Write-Host "Applying Kubernetes manifests..."
kubectl apply -f kubernetes/manifests/

# 6. Wait for deployments to be ready
Write-Host "Waiting for deployments to be ready..."
kubectl rollout status deployment/ui
kubectl rollout status deployment/eep1
kubectl rollout status deployment/iep1
kubectl rollout status deployment/iep2
kubectl rollout status deployment/iep3
kubectl rollout status deployment/iep4

# 7. Enable Ingress addon if needed
Write-Host "Enabling Ingress addon..."
minikube addons enable ingress

# 8. Print access information
Write-Host "`nDeployment complete!"
Write-Host "`nTo access your application:"
Write-Host "1. UI service: Run 'minikube service ui'"
Write-Host "2. If using Ingress, access via Minikube IP: $(minikube ip)"

# 9. Print basic commands for reference
Write-Host "`nUseful commands:"
Write-Host "- View all resources: kubectl get all"
Write-Host "- View logs: kubectl logs <pod-name>"
Write-Host "- Get a shell: kubectl exec -it <pod-name> -- /bin/sh"
Write-Host "- Delete all: kubectl delete -f kubernetes/manifests/"
Write-Host "- Stop Minikube: minikube stop" 