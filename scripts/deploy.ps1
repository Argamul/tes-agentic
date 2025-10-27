# NLP/AI Microservice Deployment Script (PowerShell)
# This script provides easy deployment options for the NLP/AI microservice

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("docker-build", "docker-run", "docker-stop", "k8s-deploy", "k8s-delete", "k8s-status", "test", "docs", "logs")]
    [string]$Command,
    
    [string]$Namespace = "nlp-ai",
    [string]$Environment = "development",
    [string]$ImageTag = "latest",
    [string]$Registry = "your-registry.com",
    [string]$ServiceName = "nlp-ai-service"
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to show usage
function Show-Usage {
    Write-Host "Usage: .\deploy.ps1 -Command COMMAND [OPTIONS]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  docker-build     Build Docker image"
    Write-Host "  docker-run       Run with Docker Compose"
    Write-Host "  docker-stop      Stop Docker Compose services"
    Write-Host "  k8s-deploy       Deploy to Kubernetes"
    Write-Host "  k8s-delete       Delete from Kubernetes"
    Write-Host "  k8s-status       Check Kubernetes deployment status"
    Write-Host "  test             Run tests"
    Write-Host "  docs             Generate documentation"
    Write-Host "  logs             Show logs"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Namespace NAMESPACE    Kubernetes namespace (default: nlp-ai)"
    Write-Host "  -Environment ENV        Environment (development/production) (default: development)"
    Write-Host "  -ImageTag TAG           Docker image tag (default: latest)"
    Write-Host "  -Registry REGISTRY      Docker registry (default: your-registry.com)"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\deploy.ps1 -Command docker-build"
    Write-Host "  .\deploy.ps1 -Command docker-run"
    Write-Host "  .\deploy.ps1 -Command k8s-deploy -Environment production -ImageTag v1.0.0"
    Write-Host "  .\deploy.ps1 -Command k8s-status -Namespace nlp-ai"
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check if Docker is installed
    try {
        docker --version | Out-Null
    }
    catch {
        Write-Error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    }
    
    # Check if Docker Compose is installed
    try {
        docker-compose --version | Out-Null
    }
    catch {
        Write-Error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    }
    
    Write-Success "Prerequisites check passed"
}

# Function to build Docker image
function Build-DockerImage {
    Write-Status "Building Docker image..."
    
    # Build the image
    docker build -t "${Registry}/${ServiceName}:${ImageTag}" .
    
    # Tag as latest if not already
    if ($ImageTag -ne "latest") {
        docker tag "${Registry}/${ServiceName}:${ImageTag}" "${Registry}/${ServiceName}:latest"
    }
    
    Write-Success "Docker image built successfully: ${Registry}/${ServiceName}:${ImageTag}"
}

# Function to run with Docker Compose
function Start-DockerCompose {
    Write-Status "Starting services with Docker Compose..."
    
    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Creating from env.example..."
        Copy-Item "env.example" ".env"
        Write-Warning "Please update .env file with your configuration before running again."
        exit 1
    }
    
    # Start services
    docker-compose up --build -d
    
    Write-Success "Services started successfully"
    Write-Status "Access the API at: http://localhost:8000"
    Write-Status "View API docs at: http://localhost:8000/docs"
    Write-Status "View metrics at: http://localhost:8000/metrics"
    Write-Status "View logs with: docker-compose logs -f"
}

# Function to stop Docker Compose services
function Stop-DockerCompose {
    Write-Status "Stopping Docker Compose services..."
    
    docker-compose down
    
    Write-Success "Services stopped successfully"
}

# Function to deploy to Kubernetes
function Deploy-Kubernetes {
    Write-Status "Deploying to Kubernetes..."
    
    # Check if kubectl is installed
    try {
        kubectl version --client | Out-Null
    }
    catch {
        Write-Error "kubectl is not installed. Please install kubectl first."
        exit 1
    }
    
    # Create namespace if it doesn't exist
    kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets if they don't exist
    $secretExists = kubectl get secret nlp-ai-secrets -n $Namespace 2>$null
    if (-not $secretExists) {
        Write-Warning "Creating secrets. Please update with your actual API keys."
        kubectl create secret generic nlp-ai-secrets `
            --from-literal=OPENAI_API_KEY=your_openai_key_here `
            --from-literal=ANTHROPIC_API_KEY=your_anthropic_key_here `
            --namespace=$Namespace
    }
    
    # Update image tag in deployment
    if ($ImageTag -ne "latest") {
        $deploymentContent = Get-Content "k8s/deployment.yaml" -Raw
        $deploymentContent = $deploymentContent -replace "your-registry/nlp-ai-service:latest", "${Registry}/${ServiceName}:${ImageTag}"
        Set-Content "k8s/deployment.yaml" $deploymentContent
    }
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/deployment.yaml -n $Namespace
    kubectl apply -f k8s/service.yaml -n $Namespace
    kubectl apply -f k8s/hpa.yaml -n $Namespace
    
    # Restore original deployment file
    if ($ImageTag -ne "latest") {
        git checkout k8s/deployment.yaml
    }
    
    Write-Success "Deployment completed successfully"
    Write-Status "Checking deployment status..."
    kubectl get pods -n $Namespace
}

# Function to delete from Kubernetes
function Remove-Kubernetes {
    Write-Status "Deleting from Kubernetes..."
    
    kubectl delete -f k8s/hpa.yaml -n $Namespace --ignore-not-found=true
    kubectl delete -f k8s/service.yaml -n $Namespace --ignore-not-found=true
    kubectl delete -f k8s/deployment.yaml -n $Namespace --ignore-not-found=true
    
    Write-Success "Deletion completed successfully"
}

# Function to check Kubernetes status
function Get-KubernetesStatus {
    Write-Status "Checking Kubernetes deployment status..."
    
    Write-Host ""
    Write-Host "=== Pods ===" -ForegroundColor Cyan
    kubectl get pods -n $Namespace
    
    Write-Host ""
    Write-Host "=== Services ===" -ForegroundColor Cyan
    kubectl get services -n $Namespace
    
    Write-Host ""
    Write-Host "=== HPA ===" -ForegroundColor Cyan
    kubectl get hpa -n $Namespace
    
    Write-Host ""
    Write-Host "=== Events ===" -ForegroundColor Cyan
    kubectl get events -n $Namespace --sort-by='.lastTimestamp' | Select-Object -Last 10
}

# Function to run tests
function Invoke-Tests {
    Write-Status "Running tests..."
    
    # Run simple E2E tests
    python -m pytest tests/test_simple_e2e.py -v
    
    # Run other tests if they exist
    if (Test-Path "tests/test_llm_integration.py") {
        python -m pytest tests/test_llm_integration.py -v
    }
    
    if (Test-Path "tests/test_vector_search_educational.py") {
        python -m pytest tests/test_vector_search_educational.py -v
    }
    
    Write-Success "Tests completed successfully"
}

# Function to generate documentation
function New-Documentation {
    Write-Status "Generating documentation..."
    
    # Generate OpenAPI documentation
    python scripts/generate_openapi_simple.py
    
    Write-Success "Documentation generated successfully"
    Write-Status "View API docs at: docs/api/redoc.html"
}

# Function to show logs
function Show-Logs {
    Write-Status "Showing logs..."
    
    if ($Environment -eq "development") {
        docker-compose logs -f
    }
    else {
        kubectl logs -f deployment/$ServiceName -n $Namespace
    }
}

# Main execution
try {
    switch ($Command) {
        "docker-build" {
            Test-Prerequisites
            Build-DockerImage
        }
        "docker-run" {
            Test-Prerequisites
            Start-DockerCompose
        }
        "docker-stop" {
            Stop-DockerCompose
        }
        "k8s-deploy" {
            Test-Prerequisites
            Deploy-Kubernetes
        }
        "k8s-delete" {
            Remove-Kubernetes
        }
        "k8s-status" {
            Get-KubernetesStatus
        }
        "test" {
            Invoke-Tests
        }
        "docs" {
            New-Documentation
        }
        "logs" {
            Show-Logs
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Usage
            exit 1
        }
    }
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    exit 1
}



