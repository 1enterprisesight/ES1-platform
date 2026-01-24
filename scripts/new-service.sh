#!/usr/bin/env bash
# Scaffold a new service from a template
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 <service-name> <template-type>"
    echo ""
    echo "Arguments:"
    echo "  service-name    Name of the new service (e.g., user-service)"
    echo "  template-type   One of: python, node, go"
    echo ""
    echo "Example:"
    echo "  $0 user-service python"
    exit 1
}

if [[ $# -lt 2 ]]; then
    usage
fi

SERVICE_NAME="$1"
TEMPLATE_TYPE="$2"

# Validate template type
case "$TEMPLATE_TYPE" in
    python|node|go)
        TEMPLATE_DIR="$PROJECT_ROOT/services/service-template-$TEMPLATE_TYPE"
        ;;
    *)
        echo "ERROR: Invalid template type: $TEMPLATE_TYPE"
        echo "Valid options: python, node, go"
        exit 1
        ;;
esac

# Validate service name
if [[ ! "$SERVICE_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
    echo "ERROR: Service name must start with a letter and contain only lowercase letters, numbers, and hyphens"
    exit 1
fi

SERVICE_DIR="$PROJECT_ROOT/services/$SERVICE_NAME"

# Check if service already exists
if [[ -d "$SERVICE_DIR" ]]; then
    echo "ERROR: Service already exists: $SERVICE_DIR"
    exit 1
fi

echo "=== Creating New Service ==="
echo "Name: $SERVICE_NAME"
echo "Template: $TEMPLATE_TYPE"
echo ""

# Copy template
cp -r "$TEMPLATE_DIR" "$SERVICE_DIR"

# Replace template placeholders
find "$SERVICE_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.go" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) | while read -r file; do
    # Replace service name placeholder
    sed -i '' "s/service-template-$TEMPLATE_TYPE/$SERVICE_NAME/g" "$file" 2>/dev/null || \
    sed -i "s/service-template-$TEMPLATE_TYPE/$SERVICE_NAME/g" "$file"
done

# Create K8s manifests directory
K8S_SERVICE_DIR="$PROJECT_ROOT/k8s/base/services/$SERVICE_NAME"
mkdir -p "$K8S_SERVICE_DIR"

# Create basic K8s manifests
cat > "$K8S_SERVICE_DIR/deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $SERVICE_NAME
  namespace: es1-platform
  labels:
    app: $SERVICE_NAME
spec:
  replicas: 2
  selector:
    matchLabels:
      app: $SERVICE_NAME
  template:
    metadata:
      labels:
        app: $SERVICE_NAME
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: $SERVICE_NAME
          image: ghcr.io/1enterprisesight/es1-platform/$SERVICE_NAME:latest
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
EOF

cat > "$K8S_SERVICE_DIR/service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: $SERVICE_NAME
  namespace: es1-platform
spec:
  selector:
    app: $SERVICE_NAME
  ports:
    - port: 80
      targetPort: 8000
EOF

cat > "$K8S_SERVICE_DIR/kustomization.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
EOF

echo "✓ Created service: $SERVICE_DIR"
echo "✓ Created K8s manifests: $K8S_SERVICE_DIR"
echo ""
echo "Next steps:"
echo "  1. Update the base kustomization.yaml to include the new service"
echo "  2. Implement your service logic in services/$SERVICE_NAME/src/"
echo "  3. Build: docker build -t ghcr.io/1enterprisesight/es1-platform/$SERVICE_NAME:local services/$SERVICE_NAME"
echo "  4. Deploy: kubectl apply -k k8s/overlays/local"
