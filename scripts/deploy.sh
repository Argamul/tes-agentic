#!/bin/bash

# NLP/AI Microservice Deployment Script
# This script provides easy deployment options for the NLP/AI microservice

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
NAMESPACE="nlp-ai"
ENVIRONMENT="development"
IMAGE_TAG="latest"
REGISTRY="your-registry.com"
SERVICE_NAME="nlp-ai-service"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "Commands:"
    echo "  docker-build     Build Docker image"
    echo "  docker-run       Run with Docker Compose"
    echo "  k8s-deploy       Deploy to Kubernetes"
    echo "  k8s-delete       Delete from Kubernetes"
    echo "  k8s-status       Check Kubernetes deployment status"
    echo "  test             Run tests"
    echo "  docs             Generate documentation"
    echo ""
    echo "Options:"
    echo "  -n, --namespace NAMESPACE    Kubernetes namespace (default: nlp-ai)"
    echo "  -e, --environment ENV        Environment (development/production) (default: development)"
    echo "  -t, --tag TAG               Docker image tag (default: latest)"
    echo "  -r, --registry REGISTRY     Docker registry (default: your-registry.com)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 docker-build"
    echo "  $0 docker-run"
    echo "  $0 k8s-deploy -e production -t v1.0.0"
    echo "  $0 k8s-status -n nlp-ai"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to build Docker image
docker_build() {
    print_status "Building Docker image..."
    
    # Build the image
    docker build -t ${REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG} .
    
    # Tag as latest if not already
    if [ "${IMAGE_TAG}" != "latest" ]; then
        docker tag ${REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG} ${REGISTRY}/${SERVICE_NAME}:latest
    fi
    
    print_success "Docker image built successfully: ${REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG}"
}

# Function to run with Docker Compose
docker_run() {
    print_status "Starting services with Docker Compose..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from env.example..."
        cp env.example .env
        print_warning "Please update .env file with your configuration before running again."
        exit 1
    fi
    
    # Start services
    docker-compose up --build -d
    
    print_success "Services started successfully"
    print_status "Access the API at: http://localhost:8000"
    print_status "View API docs at: http://localhost:8000/docs"
    print_status "View metrics at: http://localhost:8000/metrics"
    print_status "View logs with: docker-compose logs -f"
}

# Function to deploy to Kubernetes
k8s_deploy() {
    print_status "Deploying to Kubernetes..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secrets if they don't exist
    if ! kubectl get secret nlp-ai-secrets -n ${NAMESPACE} &> /dev/null; then
        print_warning "Creating secrets. Please update with your actual API keys."
        kubectl create secret generic nlp-ai-secrets \
            --from-literal=OPENAI_API_KEY=your_openai_key_here \
            --from-literal=ANTHROPIC_API_KEY=your_anthropic_key_here \
            --namespace=${NAMESPACE}
    fi
    
    # Update image tag in deployment
    if [ "${IMAGE_TAG}" != "latest" ]; then
        sed -i.bak "s|your-registry/nlp-ai-service:latest|${REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG}|g" k8s/deployment.yaml
    fi
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
    kubectl apply -f k8s/hpa.yaml -n ${NAMESPACE}
    
    # Restore original deployment file
    if [ -f k8s/deployment.yaml.bak ]; then
        mv k8s/deployment.yaml.bak k8s/deployment.yaml
    fi
    
    print_success "Deployment completed successfully"
    print_status "Checking deployment status..."
    kubectl get pods -n ${NAMESPACE}
}

# Function to delete from Kubernetes
k8s_delete() {
    print_status "Deleting from Kubernetes..."
    
    kubectl delete -f k8s/hpa.yaml -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete -f k8s/service.yaml -n ${NAMESPACE} --ignore-not-found=true
    kubectl delete -f k8s/deployment.yaml -n ${NAMESPACE} --ignore-not-found=true
    
    print_success "Deletion completed successfully"
}

# Function to check Kubernetes status
k8s_status() {
    print_status "Checking Kubernetes deployment status..."
    
    echo ""
    echo "=== Pods ==="
    kubectl get pods -n ${NAMESPACE}
    
    echo ""
    echo "=== Services ==="
    kubectl get services -n ${NAMESPACE}
    
    echo ""
    echo "=== HPA ==="
    kubectl get hpa -n ${NAMESPACE}
    
    echo ""
    echo "=== Events ==="
    kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -10
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Run simple E2E tests
    python -m pytest tests/test_simple_e2e.py -v
    
    # Run other tests if they exist
    if [ -f "tests/test_llm_integration.py" ]; then
        python -m pytest tests/test_llm_integration.py -v
    fi
    
    if [ -f "tests/test_vector_search_educational.py" ]; then
        python -m pytest tests/test_vector_search_educational.py -v
    fi
    
    print_success "Tests completed successfully"
}

# Function to generate documentation
generate_docs() {
    print_status "Generating documentation..."
    
    # Generate OpenAPI documentation
    python scripts/generate_openapi_simple.py
    
    print_success "Documentation generated successfully"
    print_status "View API docs at: docs/api/redoc.html"
}

# Function to stop Docker Compose services
docker_stop() {
    print_status "Stopping Docker Compose services..."
    
    docker-compose down
    
    print_success "Services stopped successfully"
}

# Function to show logs
show_logs() {
    print_status "Showing logs..."
    
    if [ "${ENVIRONMENT}" = "development" ]; then
        docker-compose logs -f
    else
        kubectl logs -f deployment/${SERVICE_NAME} -n ${NAMESPACE}
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        docker-build)
            COMMAND="docker-build"
            shift
            ;;
        docker-run)
            COMMAND="docker-run"
            shift
            ;;
        docker-stop)
            COMMAND="docker-stop"
            shift
            ;;
        k8s-deploy)
            COMMAND="k8s-deploy"
            shift
            ;;
        k8s-delete)
            COMMAND="k8s-delete"
            shift
            ;;
        k8s-status)
            COMMAND="k8s-status"
            shift
            ;;
        test)
            COMMAND="test"
            shift
            ;;
        docs)
            COMMAND="docs"
            shift
            ;;
        logs)
            COMMAND="logs"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if command is provided
if [ -z "${COMMAND}" ]; then
    print_error "No command provided"
    show_usage
    exit 1
fi

# Execute command
case ${COMMAND} in
    docker-build)
        check_prerequisites
        docker_build
        ;;
    docker-run)
        check_prerequisites
        docker_run
        ;;
    docker-stop)
        docker_stop
        ;;
    k8s-deploy)
        check_prerequisites
        k8s_deploy
        ;;
    k8s-delete)
        k8s_delete
        ;;
    k8s-status)
        k8s_status
        ;;
    test)
        run_tests
        ;;
    docs)
        generate_docs
        ;;
    logs)
        show_logs
        ;;
    *)
        print_error "Unknown command: ${COMMAND}"
        show_usage
        exit 1
        ;;
esac



