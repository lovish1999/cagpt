# Kubernetes Deployment Guide for CA-GPT

## Prerequisites
- Docker installed
- kubectl installed
- A Kubernetes cluster (GKE, Minikube, etc.)
- Docker Hub account (or other container registry)

## Step 1: Build and Push Docker Image

```bash
# Build the Docker image
docker build -t lovish1999/cagpt:latest .

# Test locally (optional)
docker run -p 8000:8000 -e OPENAI_API_KEY=your-key lovish1999/cagpt:latest

# Push to Docker Hub (login first if needed)
docker login
docker push lovish1999/cagpt:latest
```

## Step 2: Create Secret with Your API Key

```bash
# Copy the template
cp k8s/secret.yaml.template k8s/secret.yaml

# Edit k8s/secret.yaml and replace 'your-openai-api-key-here' with your actual API key
# Then apply it
kubectl apply -f k8s/secret.yaml
```

## Step 3: Deploy to Kubernetes

```bash
# Apply ConfigMap (non-sensitive config)
kubectl apply -f k8s/configmap.yaml

# Apply Deployment
kubectl apply -f k8s/deployment.yaml

# Apply Service
kubectl apply -f k8s/service.yaml
```

## Step 4: Verify Deployment

```bash
# Check pod status
kubectl get pods

# Check service status
kubectl get services

# Get logs
kubectl logs -l app=cagpt

# Get external IP (for cloud providers)
kubectl get service cagpt-service
```

## Step 5: Access Your Application

### For Cloud Providers (GKE, AKS, etc.):
```bash
# Wait for external IP to be assigned
kubectl get service cagpt-service -w

# Once you have EXTERNAL-IP, access at:
# http://<EXTERNAL-IP>
```

### For Minikube:
```bash
# Use minikube service to get URL
minikube service cagpt-service --url
```

## Updating the Application

```bash
# After code changes:
docker build -t lovish1999/cagpt:latest .
docker push lovish1999/cagpt:latest

# Restart pods to pull new image
kubectl rollout restart deployment cagpt-deployment
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/
```

## Platform-Specific Notes

### Google Kubernetes Engine (GKE)
```bash
# Create cluster (free tier eligible)
gcloud container clusters create cagpt-cluster \
  --zone us-central1-a \
  --num-nodes 1 \
  --machine-type e2-micro

# Get credentials
gcloud container clusters get-credentials cagpt-cluster --zone us-central1-a
```

### Oracle Cloud
- Use ARM-based instances (always free)
- Follow OCI container engine documentation

### Minikube (Local)
```bash
# Start minikube
minikube start

# Use NodePort instead of LoadBalancer
# Edit service.yaml: change type to NodePort

# Access service
minikube service cagpt-service
```

## Troubleshooting

```bash
# Check pod logs
kubectl logs -l app=cagpt --tail=100

# Describe pod for events
kubectl describe pod -l app=cagpt

# Check if secret is created
kubectl get secrets

# Check if configmap is created
kubectl get configmaps
```
