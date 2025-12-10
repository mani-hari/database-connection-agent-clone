# GKE → Cloud SQL Connection Guide

This file contains the complete instructions for connecting a GKE cluster to Cloud SQL.
**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Variables available from previous steps:**
- `PROJECT_ID` - GCP project ID
- `USER_EMAIL` - Authenticated user email
- `CLOUDSQL_INSTANCE_NAME` - Selected Cloud SQL instance
- `CLOUDSQL_REGION` - Cloud SQL region
- `CLOUDSQL_DATABASE_VERSION` - Database type (POSTGRES_XX, MYSQL_X_X, SQLSERVER_XXXX)

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
Present clusters as numbered list. Accept number or name input.

Capture and store:
- `GKE_CLUSTER_NAME`
- `GKE_CLUSTER_LOCATION` (zone or region)

### 2C.4 Get Cluster Credentials
```bash
gcloud container clusters get-credentials GKE_CLUSTER_NAME --location=GKE_CLUSTER_LOCATION
```

### 2C.5 Select Namespace
```bash
kubectl get namespaces --no-headers -o custom-columns=":metadata.name"
```

Present namespaces and allow selection, default to `default`.

Store: `K8S_NAMESPACE`

Display confirmation:
```
✅ Selected cluster: [GKE_CLUSTER_NAME] in [GKE_CLUSTER_LOCATION]
✅ Namespace: [K8S_NAMESPACE]
✅ kubectl context configured
```

**→ Ask: "Ready to proceed to Step 3 (Network Validation)? (yes/no)"**

---

## Step 3C: GKE Network Validation

### 3C.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,region)"
```

Extract and store:
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork)
- `CLOUDSQL_CONNECTION_NAME` (format: project:region:instance)

### 3C.2 Gather GKE Cluster Details
```bash
gcloud container clusters describe GKE_CLUSTER_NAME --location=GKE_CLUSTER_LOCATION --format="yaml(name,network,subnetwork,privateClusterConfig,workloadIdentityConfig,ipAllocationPolicy)"
```

Extract and store:
- `GKE_VPC` (from network)
- `GKE_SUBNET` (from subnetwork)
- `WORKLOAD_IDENTITY_ENABLED` (true if workloadIdentityConfig.workloadPool exists)
- `WORKLOAD_POOL` (from workloadIdentityConfig.workloadPool, format: PROJECT_ID.svc.id.goog)
- `VPC_NATIVE` (true if ipAllocationPolicy.useIpAliases is true)
- `PRIVATE_CLUSTER` (true if privateClusterConfig.enablePrivateNodes is true)

### 3C.3 Check Subnet Private Google Access
```bash
gcloud compute networks subnets describe GKE_SUBNET --region=REGION --format="value(privateIpGoogleAccess)"
```

### 3C.4 Network Analysis Output
```
╔══════════════════════════════════════════════════════════════════╗
║                    GKE NETWORK ANALYSIS RESULTS                   ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ GKE Cluster: [GKE_CLUSTER_NAME]                                   ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅ / ❌  │ [IP or "Not enabled"] ║
║ Cloud SQL Public IP            │ ✅ / ❌  │ [IP or "Not enabled"] ║
║ GKE VPC-Native Mode            │ ✅ / ❌  │ [Enabled/Disabled]    ║
║ Same VPC Network               │ ✅ / ❌  │ [VPC names]           ║
║ Private Google Access          │ ✅ / ❌  │ [Enabled/Disabled]    ║
║ Workload Identity              │ ✅ / ❌  │ [Pool name or "None"] ║
║ Private Cluster                │ ✅ / ❌  │ [Yes/No]              ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED CONNECTION METHOD:                                    ║
║ [Workload Identity + Auth Proxy Sidecar / Service Account Key]   ║
╚══════════════════════════════════════════════════════════════════╝
```

### 3C.5 Connectivity Decision Tree

**If Workload Identity enabled AND same VPC:**
- Recommend: Cloud SQL Auth Proxy sidecar with Workload Identity
- Most secure option, no secrets needed in cluster
- Proceed to 3C.6 for Workload Identity setup

**If Workload Identity NOT enabled:**
- Recommend: Enable Workload Identity (more secure) OR use service account key
- Offer to enable Workload Identity
- If declined, provide service account key method

**If different VPC:**
- Recommend: VPC Peering between GKE VPC and Cloud SQL VPC
- Or move Cloud SQL to GKE VPC

**If only Public IP:**
- Recommend: Cloud SQL Auth Proxy sidecar (works with public IP)
- Warn about security implications

### 3C.6 Workload Identity Setup (Recommended Path)

**Step 1: Enable Workload Identity on Cluster (if not enabled):**
```bash
gcloud container clusters update GKE_CLUSTER_NAME \
  --location=GKE_CLUSTER_LOCATION \
  --workload-pool=PROJECT_ID.svc.id.goog
```

**Step 2: Update Node Pool for Workload Identity:**
```bash
gcloud container node-pools update default-pool \
  --cluster=GKE_CLUSTER_NAME \
  --location=GKE_CLUSTER_LOCATION \
  --workload-metadata=GKE_METADATA
```

**Step 3: Create GCP Service Account for Cloud SQL:**
```bash
gcloud iam service-accounts create cloudsql-sa \
  --display-name="Cloud SQL Service Account for GKE"
```

**Step 4: Grant Cloud SQL Client Role to Service Account:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

**Step 5: Create Kubernetes Service Account:**
```bash
kubectl create serviceaccount cloudsql-sa --namespace=K8S_NAMESPACE
```

**Step 6: Bind Kubernetes SA to GCP SA (Workload Identity):**
```bash
gcloud iam service-accounts add-iam-policy-binding \
  cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[K8S_NAMESPACE/cloudsql-sa]"
```

**Step 7: Annotate Kubernetes Service Account:**
```bash
kubectl annotate serviceaccount cloudsql-sa \
  --namespace=K8S_NAMESPACE \
  iam.gke.io/gcp-service-account=cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com
```

### 3C.7 Enable Private Google Access (if needed)
```bash
gcloud compute networks subnets update GKE_SUBNET \
  --region=REGION \
  --enable-private-ip-google-access
```

**→ Ask: "Ready to proceed to Step 4 (Deployment Configuration)? (yes/no)"**

---

## Step 4C: GKE Deployment and Code

### 4C.1 Connection Summary
```
CONNECTION SUMMARY
─────────────────────────────────
Method: Cloud SQL Auth Proxy Sidecar
Cloud SQL Instance: [CLOUDSQL_CONNECTION_NAME]
GKE Cluster: [GKE_CLUSTER_NAME]
Namespace: [K8S_NAMESPACE]
Workload Identity: [Enabled/Disabled]
Service Account: cloudsql-sa
─────────────────────────────────
```

### 4C.2 Create Database Credentials Secret
```bash
kubectl create secret generic cloudsql-db-credentials \
  --namespace=K8S_NAMESPACE \
  --from-literal=username=YOUR_DB_USER \
  --from-literal=password=YOUR_DB_PASSWORD \
  --from-literal=database=YOUR_DB_NAME
```

### 4C.3 Deployment with Auth Proxy Sidecar

Provide the appropriate deployment YAML based on database type:

**PostgreSQL Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: K8S_NAMESPACE
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
          value: "5432"
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
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

      # Cloud SQL Auth Proxy sidecar
      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
        args:
          - "--structured-logs"
          - "--auto-iam-authn"
          - "CLOUDSQL_CONNECTION_NAME"
        securityContext:
          runAsNonRoot: true
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**MySQL Deployment (port 3306):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: K8S_NAMESPACE
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
      - name: my-app
        image: YOUR_APP_IMAGE
        env:
        - name: DB_HOST
          value: "127.0.0.1"
        - name: DB_PORT
          value: "3306"
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

      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.14.1
        args:
          - "--structured-logs"
          - "--auto-iam-authn"
          - "CLOUDSQL_CONNECTION_NAME"
        securityContext:
          runAsNonRoot: true
```

### 4C.4 Apply Deployment
```bash
kubectl apply -f deployment.yaml
```

### 4C.5 Verify Deployment
```bash
kubectl get pods -n K8S_NAMESPACE -l app=my-app
```

Check proxy logs:
```bash
kubectl logs -n K8S_NAMESPACE deployment/my-app -c cloud-sql-proxy
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

**Go (connecting via sidecar):**
```go
package main

import (
    "database/sql"
    "fmt"
    "os"
    _ "github.com/lib/pq"
)

func connectDB() (*sql.DB, error) {
    host := os.Getenv("DB_HOST")
    if host == "" {
        host = "127.0.0.1"
    }
    port := os.Getenv("DB_PORT")
    if port == "" {
        port = "5432"
    }

    dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
        host, port, os.Getenv("DB_USER"), os.Getenv("DB_PASS"), os.Getenv("DB_NAME"))

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Java (connecting via sidecar):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    public static Connection getConnection() throws SQLException {
        String host = System.getenv().getOrDefault("DB_HOST", "127.0.0.1");
        String port = System.getenv().getOrDefault("DB_PORT", "5432");
        String dbName = System.getenv("DB_NAME");
        String user = System.getenv("DB_USER");
        String pass = System.getenv("DB_PASS");

        String url = String.format("jdbc:postgresql://%s:%s/%s", host, port, dbName);
        return DriverManager.getConnection(url, user, pass);
    }
}
```

### 4C.7 Service (Optional - for exposing your app)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-service
  namespace: K8S_NAMESPACE
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### 4C.8 Next Steps for Production

Display these recommendations:
```
PRODUCTION RECOMMENDATIONS
─────────────────────────────────
1. Secret Management:
   - Use Secret Manager with External Secrets Operator
   - Or use Workload Identity with IAM database authentication

2. High Availability:
   - Increase replicas: replicas: 3
   - Add pod disruption budget
   - Configure pod anti-affinity

3. Security:
   - Add network policies to restrict pod traffic
   - Use private cluster if not already
   - Enable Binary Authorization

4. Monitoring:
   - Enable Cloud SQL insights
   - Set up alerts for connection errors
   - Monitor proxy sidecar resource usage

5. Connection Pooling:
   - Consider PgBouncer for PostgreSQL
   - Or ProxySQL for MySQL
─────────────────────────────────
```

---

## Completion

Display:
```
✅ GKE → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: [CLOUDSQL_INSTANCE_NAME]
- GKE Cluster: [GKE_CLUSTER_NAME]
- Namespace: [K8S_NAMESPACE]
- Method: Auth Proxy Sidecar with Workload Identity
- Service Account: cloudsql-sa

Deployment created with:
- Application container connected to localhost:PORT
- Cloud SQL Auth Proxy sidecar
- Workload Identity for secure authentication

Next steps:
1. Deploy your application image
2. Verify connection with: kubectl logs deployment/my-app -c cloud-sql-proxy
3. Set up monitoring and alerting
```
