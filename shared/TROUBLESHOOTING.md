# Cloud SQL Connection Troubleshooting Guide

Quick reference for diagnosing and resolving Cloud SQL connection issues across all compute platforms.

---

## Quick Reference Table

| Issue | Diagnostic Command | Resolution |
|-------|-------------------|------------|
| Connection timeout | `gcloud sql instances describe INSTANCE --format="yaml(ipAddresses)"` | Verify network connectivity, check firewall rules, validate Private Services Access |
| Connection refused | `nc -zv HOST PORT` or `telnet HOST PORT` | Check if instance is running, verify port number, check firewall rules |
| Access denied / Permission denied | `gcloud projects get-iam-policy PROJECT --flatten="bindings[].members" --filter="bindings.members:user:EMAIL"` | Add `roles/cloudsql.client` or `roles/cloudsql.editor` to user/service account |
| VPC mismatch | `gcloud sql instances describe INSTANCE --format="value(settings.ipConfiguration.privateNetwork)"` | Set up VPC peering or move resources to same VPC |
| Proxy won't start | `gcloud auth application-default print-access-token` | Re-authenticate with `gcloud auth application-default login` |
| Workload Identity fails (GKE) | `kubectl describe sa SA_NAME -n NAMESPACE` | Verify annotation and IAM binding between K8s SA and GCP SA |
| Port already in use | `lsof -i :PORT` or `netstat -an \| grep PORT` | Kill process using port or use different port |
| No route to host | `gcloud compute routes list --filter="network:VPC_NAME"` | Check VPC routing, verify Private Google Access enabled |

---

## Connection Errors

### Connection Timeout

**Symptoms:**
- Connection hangs indefinitely
- Error: `connection timeout` or `timeout expired`
- Application cannot reach Cloud SQL instance

**Diagnostic Commands:**
```bash
# Check Cloud SQL network configuration
gcloud sql instances describe INSTANCE_NAME --format="yaml(ipAddresses,settings.ipConfiguration)"

# Check if instance is reachable
ping CLOUDSQL_IP

# For Private IP - verify subnet configuration
gcloud compute networks subnets describe SUBNET_NAME --region=REGION --format="value(privateIpGoogleAccess)"
```

**Resolutions:**

1. **Private IP connection** - Ensure Private Services Access is configured:
```bash
# Check for existing peering
gcloud services vpc-peerings list --network=VPC_NAME --project=PROJECT_ID

# If missing, create it
gcloud compute addresses create google-managed-services-VPC_NAME \
  --global --purpose=VPC_PEERING --prefix-length=16 --network=VPC_NAME

gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-VPC_NAME \
  --network=VPC_NAME
```

2. **Check firewall rules** - Verify egress is allowed:
```bash
gcloud compute firewall-rules list --filter="network:VPC_NAME AND direction=EGRESS" \
  --format="table(name,allowed,targetTags)"
```

3. **Enable Private Google Access** (for private clusters):
```bash
gcloud compute networks subnets update SUBNET_NAME \
  --region=REGION \
  --enable-private-ip-google-access
```

---

### Connection Refused

**Symptoms:**
- Error: `connection refused`
- Error: `could not connect to server`
- Immediate connection failure

**Diagnostic Commands:**
```bash
# Check instance status
gcloud sql instances describe INSTANCE_NAME --format="value(state)"

# Test port connectivity
nc -zv CLOUDSQL_IP PORT    # Linux/Mac
Test-NetConnection -ComputerName CLOUDSQL_IP -Port PORT  # Windows PowerShell

# Verify instance is running
gcloud sql instances list --filter="name:INSTANCE_NAME"
```

**Resolutions:**

1. **Start instance if stopped:**
```bash
gcloud sql instances patch INSTANCE_NAME --activation-policy=ALWAYS
```

2. **Verify correct port:**
   - PostgreSQL: 5432
   - MySQL: 3306
   - SQL Server: 1433

3. **Check Public IP is enabled** (if connecting via public IP):
```bash
gcloud sql instances patch INSTANCE_NAME --assign-ip
```

---

### Access Denied / Permission Denied

**Symptoms:**
- Error: `Access denied for user`
- Error: `permission denied`
- Error: `The client is not authorized`

**Diagnostic Commands:**
```bash
# Check IAM permissions
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:USER_EMAIL" \
  --format="table(bindings.role)"

# For service accounts
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL" \
  --format="table(bindings.role)"

# Check database user permissions
gcloud sql users list --instance=INSTANCE_NAME
```

**Resolutions:**

1. **Grant Cloud SQL Client role:**
```bash
# For user accounts
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:USER_EMAIL" \
  --role="roles/cloudsql.client"

# For service accounts
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/cloudsql.client"
```

2. **Create database user if missing:**
```bash
# PostgreSQL
gcloud sql users create DB_USER --instance=INSTANCE_NAME --password=PASSWORD

# MySQL
gcloud sql users create DB_USER --instance=INSTANCE_NAME --host=% --password=PASSWORD
```

3. **Reset database password:**
```bash
gcloud sql users set-password DB_USER --instance=INSTANCE_NAME --password=NEW_PASSWORD
```

---

## Authentication Issues

### gcloud Auth Problems

**Symptoms:**
- Error: `gcloud: command not found`
- Error: `You do not currently have an active account selected`
- Error: `invalid authentication credentials`

**Diagnostic Commands:**
```bash
# Check active account
gcloud auth list --filter=status:ACTIVE --format="value(account)"

# Check active project
gcloud config get-value project

# Check Application Default Credentials
gcloud auth application-default print-access-token
```

**Resolutions:**

1. **Login to gcloud:**
```bash
gcloud auth login
```

2. **Set active project:**
```bash
gcloud config set project PROJECT_ID
```

3. **Set Application Default Credentials:**
```bash
gcloud auth application-default login
```

4. **For service accounts:**
```bash
gcloud auth activate-service-account SA_EMAIL --key-file=KEY_FILE.json
```

---

### Service Account Issues

**Symptoms:**
- Error: `service account does not exist`
- Error: `service account lacks necessary permissions`
- Auth Proxy fails with credential errors

**Diagnostic Commands:**
```bash
# List service accounts
gcloud iam service-accounts list --filter="email:SA_NAME"

# Check service account keys
gcloud iam service-accounts keys list --iam-account=SA_EMAIL

# Check service account permissions
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:SA_EMAIL"
```

**Resolutions:**

1. **Create service account:**
```bash
gcloud iam service-accounts create SA_NAME \
  --display-name="Cloud SQL Service Account"
```

2. **Grant required roles:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/cloudsql.client"
```

3. **Create new key (if needed):**
```bash
gcloud iam service-accounts keys create key.json --iam-account=SA_EMAIL
```

---

### Workload Identity Failures (GKE)

**Symptoms:**
- Pod cannot connect to Cloud SQL
- Error: `failed to get token for service account`
- Auth Proxy sidecar shows authentication errors

**Diagnostic Commands:**
```bash
# Check Workload Identity on cluster
gcloud container clusters describe CLUSTER_NAME --location=LOCATION \
  --format="value(workloadIdentityConfig.workloadPool)"

# Check K8s service account annotation
kubectl describe serviceaccount SA_NAME -n NAMESPACE

# Check IAM binding
gcloud iam service-accounts get-iam-policy GCP_SA_EMAIL --format=json
```

**Resolutions:**

1. **Enable Workload Identity on cluster:**
```bash
gcloud container clusters update CLUSTER_NAME \
  --location=LOCATION \
  --workload-pool=PROJECT_ID.svc.id.goog
```

2. **Update node pool:**
```bash
gcloud container node-pools update POOL_NAME \
  --cluster=CLUSTER_NAME \
  --location=LOCATION \
  --workload-metadata=GKE_METADATA
```

3. **Create and bind service accounts:**
```bash
# Create GCP service account
gcloud iam service-accounts create cloudsql-sa

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Create K8s service account
kubectl create serviceaccount cloudsql-sa -n NAMESPACE

# Bind K8s SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/cloudsql-sa]"

# Annotate K8s service account
kubectl annotate serviceaccount cloudsql-sa -n NAMESPACE \
  iam.gke.io/gcp-service-account=cloudsql-sa@PROJECT_ID.iam.gserviceaccount.com
```

4. **Verify pod is using correct service account:**
```bash
kubectl get pod POD_NAME -n NAMESPACE -o yaml | grep serviceAccountName
```

---

## Network Issues

### VPC Mismatch

**Symptoms:**
- Cannot connect via private IP
- Error: `No route to host`
- Different VPCs for Cloud SQL and compute resource

**Diagnostic Commands:**
```bash
# Check Cloud SQL VPC
gcloud sql instances describe INSTANCE_NAME \
  --format="value(settings.ipConfiguration.privateNetwork)"

# Check GCE VM VPC
gcloud compute instances describe VM_NAME --zone=ZONE \
  --format="value(networkInterfaces[0].network)"

# Check GKE cluster VPC
gcloud container clusters describe CLUSTER_NAME --location=LOCATION \
  --format="value(network)"
```

**Resolutions:**

1. **Move Cloud SQL to compute VPC:**
```bash
gcloud sql instances patch INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/VPC_NAME
```

2. **Set up VPC peering:**
```bash
# Create peering from VPC A to VPC B
gcloud compute networks peerings create vpc-a-to-vpc-b \
  --network=VPC_A \
  --peer-project=PROJECT_ID \
  --peer-network=VPC_B

# Create reverse peering from VPC B to VPC A
gcloud compute networks peerings create vpc-b-to-vpc-a \
  --network=VPC_B \
  --peer-project=PROJECT_ID \
  --peer-network=VPC_A
```

3. **Use Cloud SQL Auth Proxy** (works across VPCs):
```bash
./cloud-sql-proxy PROJECT_ID:REGION:INSTANCE_NAME --port=5432
```

---

### Firewall Blocking

**Symptoms:**
- Connection attempts blocked
- Egress traffic not reaching Cloud SQL
- Firewall deny logs in Cloud Logging

**Diagnostic Commands:**
```bash
# List firewall rules for VPC
gcloud compute firewall-rules list --filter="network:VPC_NAME" \
  --format="table(name,direction,allowed,denied,targetTags,sourceTags)"

# Check firewall logs
gcloud logging read "resource.type=gce_subnetwork AND logName=projects/PROJECT_ID/logs/compute.googleapis.com%2Ffirewall" \
  --limit=20 --format=json
```

**Resolutions:**

1. **Create egress firewall rule for Cloud SQL:**
```bash
# Allow egress to Cloud SQL (PostgreSQL)
gcloud compute firewall-rules create allow-cloudsql-egress \
  --network=VPC_NAME \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432 \
  --destination-ranges=CLOUDSQL_PRIVATE_IP/32

# For MySQL
gcloud compute firewall-rules create allow-cloudsql-egress-mysql \
  --network=VPC_NAME \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:3306 \
  --destination-ranges=CLOUDSQL_PRIVATE_IP/32
```

2. **Allow egress to Private Google Access range:**
```bash
gcloud compute firewall-rules create allow-google-apis \
  --network=VPC_NAME \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:443 \
  --destination-ranges=199.36.153.8/30
```

---

### Private Services Access Not Configured

**Symptoms:**
- Cannot connect to Cloud SQL private IP
- Private IP not showing in instance details
- Error: `Private services access not configured`

**Diagnostic Commands:**
```bash
# Check Private Services Access
gcloud services vpc-peerings list --network=VPC_NAME --project=PROJECT_ID

# Check allocated ranges
gcloud compute addresses list --global --filter="purpose:VPC_PEERING"
```

**Resolutions:**

1. **Enable Service Networking API:**
```bash
gcloud services enable servicenetworking.googleapis.com
```

2. **Create Private Services Access:**
```bash
# Allocate IP range
gcloud compute addresses create google-managed-services-VPC_NAME \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=VPC_NAME \
  --project=PROJECT_ID

# Create peering connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-VPC_NAME \
  --network=VPC_NAME \
  --project=PROJECT_ID
```

3. **Enable private IP on Cloud SQL instance:**
```bash
gcloud sql instances patch INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/VPC_NAME
```

---

### No Route to Host

**Symptoms:**
- Error: `No route to host`
- Cannot reach Cloud SQL private IP
- Network routing issues

**Diagnostic Commands:**
```bash
# Check routes in VPC
gcloud compute routes list --filter="network:VPC_NAME" \
  --format="table(name,network,destRange,nextHopGateway)"

# Check Private Google Access
gcloud compute networks subnets describe SUBNET_NAME --region=REGION \
  --format="value(privateIpGoogleAccess)"

# Traceroute (from VM)
gcloud compute ssh VM_NAME --zone=ZONE --command="traceroute CLOUDSQL_IP"
```

**Resolutions:**

1. **Enable Private Google Access:**
```bash
gcloud compute networks subnets update SUBNET_NAME \
  --region=REGION \
  --enable-private-ip-google-access
```

2. **Verify default route exists:**
```bash
gcloud compute routes list --filter="network:VPC_NAME AND destRange:0.0.0.0/0"
```

3. **For GKE - check pod networking:**
```bash
# Test from inside pod
kubectl run -it --rm debug --image=busybox --restart=Never -- ping CLOUDSQL_IP
```

---

## Auth Proxy Issues

### Proxy Won't Start

**Symptoms:**
- Auth Proxy exits immediately
- Error: `could not create dialer`
- Error: `failed to refresh token`

**Diagnostic Commands:**
```bash
# Test authentication
gcloud auth application-default print-access-token

# Check if proxy binary is executable
ls -la cloud-sql-proxy

# Check Cloud SQL Admin API is enabled
gcloud services list --enabled --filter="name:sqladmin.googleapis.com"

# Run proxy with verbose logging
./cloud-sql-proxy CONNECTION_NAME --port=5432 --verbose
```

**Resolutions:**

1. **Re-authenticate:**
```bash
gcloud auth application-default login
```

2. **Enable Cloud SQL Admin API:**
```bash
gcloud services enable sqladmin.googleapis.com
```

3. **Make proxy executable:**
```bash
chmod +x cloud-sql-proxy
```

4. **Verify connection name format:**
```bash
# Should be: project:region:instance
gcloud sql instances describe INSTANCE_NAME --format="value(connectionName)"
```

5. **Check IAM permissions:**
```bash
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/cloudsql.client"
```

---

### Port Already in Use

**Symptoms:**
- Error: `address already in use`
- Error: `bind: address already in use`
- Proxy fails to start on specified port

**Diagnostic Commands:**
```bash
# Find process using port (Linux/Mac)
lsof -i :PORT
netstat -tunlp | grep PORT

# Find process using port (Windows)
netstat -ano | findstr :PORT
```

**Resolutions:**

1. **Kill process using the port:**
```bash
# Linux/Mac
kill -9 PID

# Windows
taskkill /PID PID /F
```

2. **Use different port:**
```bash
./cloud-sql-proxy CONNECTION_NAME --port=5433
```

3. **Stop existing proxy:**
```bash
pkill cloud-sql-proxy
```

---

### Credential Errors

**Symptoms:**
- Error: `could not find default credentials`
- Error: `google: could not find default credentials`
- Auth Proxy authentication failures

**Diagnostic Commands:**
```bash
# Check for credentials file
ls -la ~/.config/gcloud/application_default_credentials.json

# Check GOOGLE_APPLICATION_CREDENTIALS env var
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test credentials
gcloud auth application-default print-access-token
```

**Resolutions:**

1. **Set Application Default Credentials:**
```bash
gcloud auth application-default login
```

2. **Use service account key:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
./cloud-sql-proxy CONNECTION_NAME --port=5432
```

3. **Verify credentials file is valid:**
```bash
# Check JSON syntax
cat ~/.config/gcloud/application_default_credentials.json | jq .
```

---

## Platform-Specific Issues

### GCE VM Specific

#### Cannot SSH to VM

**Diagnostic:**
```bash
# Check VM status
gcloud compute instances describe VM_NAME --zone=ZONE --format="value(status)"

# Check IAM permissions
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:USER_EMAIL AND bindings.role:roles/compute.instanceAdmin"
```

**Resolution:**
```bash
# Start stopped VM
gcloud compute instances start VM_NAME --zone=ZONE

# Grant OS Login role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:USER_EMAIL" \
  --role="roles/compute.osLogin"

# Use IAM tunnel
gcloud compute ssh VM_NAME --zone=ZONE --tunnel-through-iap
```

#### VM Cannot Resolve DNS

**Diagnostic:**
```bash
gcloud compute ssh VM_NAME --zone=ZONE --command="nslookup google.com"
```

**Resolution:**
```bash
# Check DNS configuration on VM
gcloud compute ssh VM_NAME --zone=ZONE --command="cat /etc/resolv.conf"

# Use Cloud DNS or update metadata
gcloud compute instances add-metadata VM_NAME --zone=ZONE \
  --metadata=VPC_DNS_SERVERS=169.254.169.254
```

---

### GKE Specific

#### Sidecar Container Crashes

**Diagnostic:**
```bash
# Check pod status
kubectl get pods -n NAMESPACE

# Check sidecar logs
kubectl logs POD_NAME -n NAMESPACE -c cloud-sql-proxy

# Describe pod
kubectl describe pod POD_NAME -n NAMESPACE
```

**Resolution:**

1. **Check resource limits:**
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "50m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

2. **Verify connection name in deployment:**
```bash
kubectl get deployment DEPLOYMENT_NAME -n NAMESPACE -o yaml | grep CLOUDSQL_CONNECTION_NAME
```

3. **Check security context:**
```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
```

#### Pod Cannot Reach Cloud SQL

**Diagnostic:**
```bash
# Test from pod
kubectl exec -it POD_NAME -n NAMESPACE -- ping CLOUDSQL_IP

# Check network policies
kubectl get networkpolicies -n NAMESPACE

# Check pod events
kubectl get events -n NAMESPACE --field-selector involvedObject.name=POD_NAME
```

**Resolution:**
```bash
# Allow egress in network policy
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-cloudsql
  namespace: NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: my-app
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector: {}
  - ports:
    - port: 5432
      protocol: TCP
EOF
```

---

### Cloud Run Specific

#### Cold Start Connection Failures

**Symptoms:**
- First request after idle period fails
- Error: `connection pool exhausted`
- Timeout on initial connection

**Diagnostic:**
```bash
# Check Cloud Run logs
gcloud run services logs read SERVICE_NAME --region=REGION --limit=50

# Check instance metrics
gcloud run services describe SERVICE_NAME --region=REGION \
  --format="yaml(spec.template.spec.containerConcurrency)"
```

**Resolutions:**

1. **Use Cloud SQL Connector** (handles reconnection):
```python
from google.cloud.sql.connector import Connector
connector = Connector()
```

2. **Set minimum instances:**
```bash
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --min-instances=1
```

3. **Configure connection pool settings:**
```python
pool = sqlalchemy.create_engine(
    # ...
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections before Cloud SQL times out
)
```

#### Unix Socket Connection Issues

**Symptoms:**
- Error: `No such file or directory: /cloudsql/...`
- Cannot find Unix socket
- Connection works locally but not in Cloud Run

**Diagnostic:**
```bash
# Check Cloud SQL connection annotation
gcloud run services describe SERVICE_NAME --region=REGION \
  --format="yaml(spec.template.metadata.annotations)"

# Check logs for socket path
gcloud run services logs read SERVICE_NAME --region=REGION | grep cloudsql
```

**Resolutions:**

1. **Verify connection name in deployment:**
```bash
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME
```

2. **Use correct Unix socket path:**
```python
# PostgreSQL
unix_socket = f"/cloudsql/{CONNECTION_NAME}/.s.PGSQL.5432"

# MySQL
unix_socket = f"/cloudsql/{CONNECTION_NAME}"
```

3. **Check environment variable:**
```bash
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --set-env-vars="INSTANCE_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME"
```

#### VPC Connector Issues

**Symptoms:**
- Cannot connect via private IP
- VPC connector errors
- Slow connections or timeouts

**Diagnostic:**
```bash
# Check VPC connector status
gcloud compute networks vpc-access connectors describe CONNECTOR_NAME \
  --region=REGION

# Check Cloud Run service VPC configuration
gcloud run services describe SERVICE_NAME --region=REGION \
  --format="yaml(spec.template.metadata.annotations)"
```

**Resolutions:**

1. **Create VPC connector:**
```bash
gcloud compute networks vpc-access connectors create CONNECTOR_NAME \
  --region=REGION \
  --network=VPC_NAME \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=10
```

2. **Update Cloud Run service:**
```bash
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --vpc-connector=CONNECTOR_NAME \
  --vpc-egress=private-ranges-only
```

3. **Check connector throughput:**
```bash
# Increase connector instances if needed
gcloud compute networks vpc-access connectors update CONNECTOR_NAME \
  --region=REGION \
  --min-instances=2 \
  --max-instances=10
```

---

### Local IDE Specific

#### Proxy Binary Not Found

**Symptoms:**
- Error: `command not found: cloud-sql-proxy`
- Cannot execute proxy
- Binary permission errors

**Diagnostic:**
```bash
# Check if binary exists
ls -la cloud-sql-proxy

# Check PATH
echo $PATH

# Check file type
file cloud-sql-proxy
```

**Resolutions:**

1. **Download correct binary for your platform:**
```bash
# macOS ARM (M1/M2/M3)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.arm64

# macOS Intel
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.amd64

# Linux
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64

# Make executable
chmod +x cloud-sql-proxy
```

2. **Move to PATH:**
```bash
sudo mv cloud-sql-proxy /usr/local/bin/
```

#### Local Application Cannot Connect to Proxy

**Symptoms:**
- Application can't connect to localhost
- Error: `Connection refused to 127.0.0.1`
- Proxy is running but connections fail

**Diagnostic:**
```bash
# Check if proxy is running
ps aux | grep cloud-sql-proxy

# Check if port is listening
netstat -an | grep PORT
lsof -i :PORT

# Test connection
nc -zv 127.0.0.1 PORT
```

**Resolutions:**

1. **Ensure proxy is running:**
```bash
./cloud-sql-proxy PROJECT_ID:REGION:INSTANCE_NAME --port=5432
```

2. **Use correct host in application:**
```python
# Use 127.0.0.1, not localhost if proxy binds to 127.0.0.1
host = "127.0.0.1"
port = 5432
```

3. **Check firewall on local machine:**
```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Linux
sudo ufw status
```

---

## Additional Debugging Tips

### Enable Detailed Logging

**Cloud SQL Proxy:**
```bash
./cloud-sql-proxy CONNECTION_NAME --port=5432 --verbose
```

**PostgreSQL client:**
```bash
PGSSLMODE=require psql "host=127.0.0.1 port=5432 dbname=DB_NAME user=DB_USER" --echo-all
```

**Cloud SQL instance logs:**
```bash
gcloud sql operations list --instance=INSTANCE_NAME --limit=10
```

### Check Cloud SQL Quotas

```bash
gcloud compute project-info describe --project=PROJECT_ID \
  --format="yaml(quotas)"
```

### Monitor Active Connections

```bash
# PostgreSQL
gcloud sql connect INSTANCE_NAME --user=postgres
SELECT * FROM pg_stat_activity;

# MySQL
gcloud sql connect INSTANCE_NAME --user=root
SHOW PROCESSLIST;
```

### Test with gcloud sql connect

```bash
# Quick test using gcloud's built-in proxy
gcloud sql connect INSTANCE_NAME --user=DB_USER --quiet
```

---

## Common Error Messages

| Error Message | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| `dial tcp: lookup instance: no such host` | Instance name incorrect | Verify instance name and connection string format |
| `Error 403: The client is not authorized` | Missing IAM permissions | Add `roles/cloudsql.client` |
| `Error 409: Instance already exists` | Instance name conflict | Choose different instance name |
| `connection timeout` | Network/firewall issue | Check VPC, firewall rules, Private Services Access |
| `password authentication failed` | Wrong credentials | Reset password or check username |
| `SSL is required` | SSL mode incorrect | Add `?sslmode=require` to connection string |
| `too many connections` | Connection limit reached | Close idle connections or increase max_connections |
| `could not create cloudsql client` | API not enabled | Enable Cloud SQL Admin API |
| `default credentials not found` | Not authenticated | Run `gcloud auth application-default login` |

---

## Support and Documentation

- **Cloud SQL Documentation:** https://cloud.google.com/sql/docs
- **Connection Overview:** https://cloud.google.com/sql/docs/postgres/connect-overview
- **Auth Proxy Guide:** https://cloud.google.com/sql/docs/postgres/sql-proxy
- **Troubleshooting Guide:** https://cloud.google.com/sql/docs/postgres/troubleshooting
- **Stack Overflow:** https://stackoverflow.com/questions/tagged/google-cloud-sql
