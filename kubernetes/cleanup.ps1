Write-Host "Cleaning up Lock-in application from Minikube..."

# Check if kubectl is available
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl is not installed!"
    exit 1
}

# Check if Minikube is running
$minikubeStatus = minikube status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Minikube is not running. Nothing to clean up."
    exit 0
}

# 1. Delete all resources
Write-Host "Deleting all Kubernetes resources..."
kubectl delete -f manifests/

# 2. Ask if Minikube should be stopped
$stopMinikube = Read-Host "Do you want to stop Minikube? (y/n)"
if ($stopMinikube -eq "y") {
    Write-Host "Stopping Minikube..."
    minikube stop
}

# 3. Ask if Minikube should be deleted
$deleteMinikube = Read-Host "Do you want to delete the Minikube cluster? (y/n)"
if ($deleteMinikube -eq "y") {
    Write-Host "Deleting Minikube cluster..."
    minikube delete
}

Write-Host "Cleanup complete!" 