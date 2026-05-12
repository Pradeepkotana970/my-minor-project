# Kubernetes Deployment Guide - Smart Monitoring System v2.0

## 📋 Prerequisites

### Required Tools
```bash
# Install or verify installation
kubectl version --client
helm version
docker --version

# Create directory
mkdir -p k8s-deployment && cd k8s-deployment
```

### Kubernetes Cluster Setup

**Option 1: Local Testing (Minikube)**
```bash
# Install Minikube
curl -LO https://github.com/kubernetes/minikube/releases/latest/download/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start cluster
minikube start --cpus=4 --memory=8192 --disk-size=50gb
minikube addons enable ingress
minikube addons enable metrics-server
```

**Option 2: AWS (EKS)**
```bash
# Prerequisites: AWS CLI configured
aws eks create-cluster \
  --name monitoring-system \
  --version 1.27 \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/eks-service-role \
  --resources-vpc-config subnetIds=subnet-xxxxx,subnet-xxxxx

# Configure kubectl
aws eks update-kubeconfig --name monitoring-system --region us-east-1
```

**Option 3: GCP (GKE)**
```bash
# Prerequisites: GCP CLI configured
gcloud container clusters create monitoring-system \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 10

# Get credentials
gcloud container clusters get-credentials monitoring-system --zone us-central1-a
```

**Option 4: Azure (AKS)**
```bash
# Create resource group
az group create --name monitoring-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group monitoring-rg \
  --name monitoring-system \
  --node-count 3 \
  --vm-set-type VirtualMachineScaleSets \
  --enable-managed-identity

# Get credentials
az aks get-credentials --resource-group monitoring-rg --name monitoring-system
```

---

## 🚀 Deployment Steps

### Step 1: Build and Push Docker Image

```bash
# Build image
docker build -t your-registry/monitoring-system:2.0 .

# Push to registry
docker push your-registry/monitoring-system:2.0

# For local Minikube (load locally)
minikube image load monitoring-system:2.0
```

### Step 2: Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace monitoring-system

# Create secrets
kubectl create secret generic monitoring-secrets \
  --from-literal=DB_PASSWORD='your-secure-password' \
  --from-literal=DB_USER='monitoring' \
  --from-literal=TWILIO_ACCOUNT_SID='your-sid' \
  --from-literal=TWILIO_AUTH_TOKEN='your-token' \
  --from-literal=TWILIO_PHONE_NUMBER='+1234567890' \
  --from-literal=SMTP_PASSWORD='your-password' \
  -n monitoring-system

# Verify
kubectl get secrets -n monitoring-system
```

### Step 3: Create Storage (for persistent data)

```bash
# For local testing
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgres-pv
  namespace: monitoring-system
spec:
  capacity:
    storage: 20Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/data/postgres"
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: monitoring-data-pv
  namespace: monitoring-system
spec:
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/data/monitoring"
EOF

# For cloud (use StorageClass)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: ebs.csi.aws.com  # For AWS, adjust for your cloud
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
EOF
```

### Step 4: Deploy Applications

```bash
# Deploy all components
kubectl apply -f kubernetes/monitoring-system.yaml

# Monitor deployment
kubectl get pods -n monitoring-system -w
kubectl get svc -n monitoring-system
kubectl describe pod monitoring-system-0 -n monitoring-system

# Check logs
kubectl logs -n monitoring-system monitoring-system-0
kubectl logs -n monitoring-system -l app=postgres
```

### Step 5: Verify Deployment

```bash
# Check StatefulSet
kubectl get statefulset -n monitoring-system
kubectl describe statefulset monitoring-system -n monitoring-system

# Check Services
kubectl get svc -n monitoring-system
kubectl get endpoints -n monitoring-system

# Test connectivity
kubectl exec -it monitoring-system-0 -n monitoring-system -- bash
  # Inside pod:
  curl http://postgres:5432
  curl http://redis:6379
  exit
```

---

## 📊 Configuration Management

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap monitoring-config -n monitoring-system

# Or apply from file
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: monitoring-config
  namespace: monitoring-system
data:
  config.py: |
    CAMERA_WIDTH = 1280
    CAMERA_HEIGHT = 720
    # ... more config
EOF

# Restart pods to apply changes
kubectl rollout restart statefulset/monitoring-system -n monitoring-system
```

### Update Secrets

```bash
# Delete and recreate (for rotation)
kubectl delete secret monitoring-secrets -n monitoring-system
kubectl create secret generic monitoring-secrets \
  --from-literal=DB_PASSWORD='new-password' \
  -n monitoring-system

# Restart pods
kubectl rollout restart statefulset/monitoring-system -n monitoring-system
```

---

## 🔄 Scaling

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale statefulset monitoring-system --replicas=5 -n monitoring-system

# Watch scaling
kubectl get pods -n monitoring-system -w
```

### Automatic Scaling (HPA)

```bash
# Check HPA status
kubectl get hpa -n monitoring-system
kubectl describe hpa monitoring-system-hpa -n monitoring-system

# Monitor scaling events
kubectl get events -n monitoring-system --sort-by='.lastTimestamp'
```

### Manual Scaling Example

```bash
# Scale based on custom metric
kubectl scale statefulset monitoring-system --replicas=10 -n monitoring-system

# This automatically scales pods from 2 to 10 based on CPU/memory usage
```

---

## 📈 Monitoring and Logging

### View Logs

```bash
# Current pod
kubectl logs -n monitoring-system monitoring-system-0

# Stream logs
kubectl logs -f -n monitoring-system monitoring-system-0

# Previous pod (if crashed)
kubectl logs --previous -n monitoring-system monitoring-system-0

# All pods of deployment
kubectl logs -l app=monitoring-system -n monitoring-system --all-containers=true

# Specific container
kubectl logs monitoring-system-0 -c monitoring-app -n monitoring-system
```

### Port Forwarding

```bash
# Access application locally
kubectl port-forward -n monitoring-system svc/monitoring-system-lb 8080:80
# Visit http://localhost:8080

# Access Grafana
kubectl port-forward -n monitoring-system svc/grafana 3000:3000
# Visit http://localhost:3000

# Access Prometheus
kubectl port-forward -n monitoring-system svc/prometheus 9090:9090
# Visit http://localhost:9090
```

### Resource Usage

```bash
# Check node resources
kubectl top nodes

# Check pod resources
kubectl top pods -n monitoring-system

# Get detailed resource info
kubectl describe node <node-name>
```

---

## 🔐 Security

### Network Policies

```bash
# Already defined in YAML, verify applied
kubectl get networkpolicy -n monitoring-system
kubectl describe networkpolicy monitoring-network-policy -n monitoring-system
```

### RBAC

```bash
# Check service account bindings
kubectl get rolebinding -n monitoring-system
kubectl describe role monitoring-system -n monitoring-system
kubectl describe rolebinding monitoring-system -n monitoring-system
```

### Pod Security Policy

```bash
# Create PSP to restrict privileged access
kubectl apply -f - <<EOF
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: monitoring-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
    seLinuxOptions:
      level: "s0:c123,c456"
EOF
```

---

## 🌐 Ingress Setup

### Install Nginx Ingress Controller

```bash
# Add Helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer
```

### Setup SSL with Cert-Manager

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF
```

---

## 📦 Upgrade and Rollback

### Rolling Update

```bash
# Update image
kubectl set image statefulset/monitoring-system \
  monitoring-app=your-registry/monitoring-system:2.1 \
  -n monitoring-system

# Watch rollout
kubectl rollout status statefulset/monitoring-system -n monitoring-system -w

# View history
kubectl rollout history statefulset/monitoring-system -n monitoring-system
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo statefulset/monitoring-system -n monitoring-system

# Rollback to specific revision
kubectl rollout undo statefulset/monitoring-system --to-revision=2 -n monitoring-system
```

---

## 🗑️ Cleanup

```bash
# Delete everything
kubectl delete namespace monitoring-system

# Or delete specific resources
kubectl delete statefulset monitoring-system -n monitoring-system
kubectl delete pvc --all -n monitoring-system
kubectl delete pv postgres-pv monitoring-data-pv -n monitoring-system
```

---

## ⚠️ Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod monitoring-system-0 -n monitoring-system

# Check events
kubectl get events -n monitoring-system --sort-by='.lastTimestamp'

# Check logs
kubectl logs monitoring-system-0 -n monitoring-system
```

### Persistent Volume Issues

```bash
# Check PVC status
kubectl get pvc -n monitoring-system
kubectl describe pvc monitoring-data-pvc -n monitoring-system

# Check PV
kubectl get pv
kubectl describe pv postgres-pv
```

### Network Connectivity

```bash
# Test DNS
kubectl exec -it monitoring-system-0 -n monitoring-system -- nslookup postgres

# Test connectivity
kubectl exec -it monitoring-system-0 -n monitoring-system -- nc -zv postgres 5432

# Check endpoints
kubectl get endpoints -n monitoring-system
```

### Performance Issues

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -n monitoring-system

# Check Pod resource requests/limits
kubectl describe pod monitoring-system-0 -n monitoring-system | grep -A 10 "Requests"

# Check HPA status
kubectl describe hpa monitoring-system-hpa -n monitoring-system
```

---

## 📋 Production Checklist

- [x] Kubernetes cluster set up (1.27+)
- [x] Storage provisioned (PVs/PVCs)
- [x] Docker images built and pushed
- [x] Secrets configured securely
- [x] StatefulSet deployed (3+ replicas)
- [x] Database initialized (PostgreSQL)
- [x] Cache configured (Redis)
- [x] Ingress set up with TLS
- [x] Monitoring active (Prometheus/Grafana)
- [x] Logging configured
- [x] RBAC policies applied
- [x] Network policies enforced
- [x] HPA configured
- [x] Backup strategy defined
- [x] Disaster recovery plan documented

---

## 🎯 Expected Results

After deployment, you should have:

✅ 3-10 monitoring system pods running
✅ PostgreSQL database operational
✅ Redis cache operational
✅ Nginx ingress handling traffic
✅ SSL/TLS certificates active
✅ Prometheus collecting metrics
✅ Grafana dashboards displaying data
✅ Auto-scaling responding to load
✅ High availability setup (replicas across nodes)
✅ Data persistence guaranteed (volumes)

Congratulations! Your Smart Monitoring System is now running on Kubernetes! 🚀
