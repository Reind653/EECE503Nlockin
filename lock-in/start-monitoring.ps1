# Start Prometheus and Grafana
Write-Host "Starting Prometheus and Grafana..." -ForegroundColor Green

# Change to the project directory
Set-Location $PSScriptRoot

# Start services with docker-compose
docker-compose up -d prometheus grafana

Write-Host "`nPrometheus and Grafana are now running!" -ForegroundColor Green
Write-Host "Access Prometheus at: http://localhost:9090" -ForegroundColor Yellow
Write-Host "Access Grafana at: http://localhost:3000" -ForegroundColor Yellow
Write-Host "`nGrafana default credentials:" -ForegroundColor Yellow
Write-Host "Username: admin" -ForegroundColor Yellow
Write-Host "Password: admin" -ForegroundColor Yellow
Write-Host "`nTo stop monitoring services, run: docker-compose down" -ForegroundColor Cyan 