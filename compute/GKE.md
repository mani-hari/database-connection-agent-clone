# GKE → Cloud SQL Connection Guide

**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

---

## Step 2C: Fetch and Select GKE Cluster

### 2C.1 Display Loading Message
```
Fetching GKE clusters... please wait
```

### 2C.2 List All GKE Clusters
```bash
gcloud container clusters list --format="table(name,location,status,currentNodeCount)"
```

### 2C.3 User Selection
Present clusters as numbered list. Accept number or name input. Capture `GKE_CLUSTER_NAME` and `GKE_CLUSTER_LOCATION`.

### 2C.4 Get Cluster Credentials
```bash
gcloud container clusters get-credentials {GKE_CLUSTER_NAME} --location={GKE_CLUSTER_LOCATION}
```

### 2C.5 Select Namespace
```bash
kubectl get namespaces --no-headers -o custom-columns=":metadata.name"
```

Present namespaces and allow selection, default to `default`. Capture `K8S_NAMESPACE`.

Display confirmation:
```
✅ Selected cluster: {GKE_CLUSTER_NAME} in {GKE_CLUSTER_LOCATION}
✅ Namespace: {K8S_NAMESPACE}
✅ kubectl context configured
```

**Auto-Complete Mode:** If user selected auto-complete in Step 2.1, skip "Ready to proceed?" prompts and continue directly. Still pause for consent before modifying resources.

**→ Ask: "Ready to proceed to Step 3 (Network Validation)? (yes/no)"**

---

## Step 3C: GKE Network Validation

### 3C.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe {CLOUDSQL_INSTANCE_NAME} --format="yaml(connectionName,ipAddresses,settings.ipConfiguration.privateNetwork)"
```

Extract and store:
- `CLOUDSQL_CONNECTION_NAME` (from connectionName field)
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE, if available)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork, if available)

### 3C.2 Gather GKE Cluster Details
```bash
gcloud container clusters describe {GKE_CLUSTER_NAME} --location={GKE_CLUSTER_LOCATION} --format="yaml(network,workloadIdentityConfig)"
```

Extract and store:
- `GKE_VPC` (from network, extract VPC name from full path)
- `WORKLOAD_IDENTITY_ENABLED` (true if workloadIdentityConfig.workloadPool exists)
- `WORKLOAD_POOL` (from workloadIdentityConfig.workloadPool if enabled)

### 3C.3 Network Analysis Output
```
╔══════════════════════════════════════════════════════════════════╗
║                    GKE NETWORK ANALYSIS RESULTS                   ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: {CLOUDSQL_INSTANCE_NAME}                     ║
║ GKE Cluster: {GKE_CLUSTER_NAME}                                   ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅ / ❌  │ {IP or "Not enabled"} ║
║ Same VPC Network               │ ✅ / ❌  │ {VPC comparison}      ║
║ Workload Identity              │ ✅ / ❌  │ {Enabled/Disabled}    ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: Cloud SQL Auth Proxy sidecar                        ║
╚══════════════════════════════════════════════════════════════════╝
```

### 3C.4 Connectivity Decision Tree

**If Workload Identity enabled:**
- ✅ Use Cloud SQL Auth Proxy sidecar with Workload Identity (recommended)
- Skip to Step 4 for deployment configuration

**If Workload Identity NOT enabled:**
- ⚠️ Recommend enabling Workload Identity (see 3C.5)

### 3C.5 Workload Identity Setup (if not enabled)

**Enable Workload Identity on Cluster:**
```bash
gcloud container clusters update {GKE_CLUSTER_NAME} \
  --location={GKE_CLUSTER_LOCATION} \
  --workload-pool={PROJECT_ID}.svc.id.goog
```

**Create GCP Service Account:**
```bash
gcloud iam service-accounts create cloudsql-sa \
  --display-name="Cloud SQL Service Account for GKE"
```

**Grant Cloud SQL Client Role:**
```bash
gcloud projects add-iam-policy-binding {PROJECT_ID} \
  --member="serviceAccount:cloudsql-sa@{PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

**Create Kubernetes Service Account:**
```bash
kubectl create serviceaccount cloudsql-sa --namespace={K8S_NAMESPACE}
```

**Bind Kubernetes SA to GCP SA:**
```bash
gcloud iam service-accounts add-iam-policy-binding \
  cloudsql-sa@{PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:{PROJECT_ID}.svc.id.goog[{K8S_NAMESPACE}/cloudsql-sa]"
```

**Annotate Kubernetes Service Account:**
```bash
kubectl annotate serviceaccount cloudsql-sa \
  --namespace={K8S_NAMESPACE} \
  iam.gke.io/gcp-service-account=cloudsql-sa@{PROJECT_ID}.iam.gserviceaccount.com
```

**→ Ask: "Ready to proceed to Step 4 (Deployment Configuration)? (yes/no)"**

---

## Step 4C: GKE Deployment and Code

### 4C.1 Connection Summary
```
CONNECTION SUMMARY
─────────────────────────────────
Method: Cloud SQL Auth Proxy Sidecar
Cloud SQL Instance: {CLOUDSQL_CONNECTION_NAME}
GKE Cluster: {GKE_CLUSTER_NAME}
Namespace: {K8S_NAMESPACE}
Workload Identity: {Enabled/Disabled}
Service Account: cloudsql-sa
─────────────────────────────────
```

### 4C.2 Create Database Credentials Secret
```bash
kubectl create secret generic cloudsql-db-credentials \
  --namespace={K8S_NAMESPACE} \
  --from-literal=username=YOUR_DB_USER \
  --from-literal=password=YOUR_DB_PASSWORD \
  --from-literal=database=YOUR_DB_NAME
```

### 4C.3 Deployment with Auth Proxy Sidecar

Provide the appropriate deployment YAML based on database type:

**Deployment YAML (adjust based on `CLOUDSQL_DATABASE_VERSION`):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: {K8S_NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: cloudsql-sa
      containers:
      # Application container
      - name: my-app
        image: YOUR_APP_IMAGE
        env:
        - name: DB_HOST
          value: "127.0.0.1"
        - name: DB_PORT
          value: "5432"  # PostgreSQL: 5432, MySQL: 3306
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: cloudsql-db-credentials
              key: username
        - name: DB_PASS
          valueFrom:
            secretKeyRef:
              name: cloudsql-db-credentials
              key: password
        - name: DB_NAME
          valueFrom:
            secretKeyRef:
              name: cloudsql-db-credentials
              key: database
        ports:
        - containerPort: 8080

      # Cloud SQL Auth Proxy sidecar
      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
        args:
          - "--structured-logs"
          - "--auto-iam-authn"
          - "{CLOUDSQL_CONNECTION_NAME}"
        securityContext:
          runAsNonRoot: true
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
```

### 4C.4 Apply Deployment
Save the YAML above to `deployment.yaml` and apply:
```bash
kubectl apply -f deployment.yaml
```

### 4C.5 Verify Deployment
```bash
kubectl get pods -n {K8S_NAMESPACE} -l app=my-app
```

Check proxy logs:
```bash
kubectl logs -n {K8S_NAMESPACE} deployment/my-app -c cloud-sql-proxy
```

### 4C.6 Application Code for GKE

**Python (connecting via sidecar):**
```python
import os
import sqlalchemy

def connect_via_proxy():
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = int(os.environ.get("DB_PORT", 5432))

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_via_proxy()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Node.js (connecting via sidecar):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  host: process.env.DB_HOST || '127.0.0.1',
  port: parseInt(process.env.DB_PORT) || 5432,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query, pool };
```

```

---

## Completion

Display:
```
✅ GKE → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: {CLOUDSQL_INSTANCE_NAME}
- GKE Cluster: {GKE_CLUSTER_NAME}
- Namespace: {K8S_NAMESPACE}
- Method: Auth Proxy Sidecar with Workload Identity
- Service Account: cloudsql-sa

Deployment created with:
- Application container connected to localhost:{PORT}
- Cloud SQL Auth Proxy sidecar
- Workload Identity for secure authentication

💡 Verify connection with: kubectl logs -n {K8S_NAMESPACE} deployment/my-app -c cloud-sql-proxy
```
