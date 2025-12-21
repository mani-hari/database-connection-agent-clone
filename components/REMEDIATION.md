# Common Cloud SQL Connection Remediation Procedures

This component contains reusable remediation procedures for Cloud SQL connectivity issues across all compute types (GCE, GKE, Cloud Run, Local IDE).

**Note:** Execute all commands only with user consent.

---

## 1. Enable Private IP on Cloud SQL

Private IP connectivity provides a secure, internal network path to Cloud SQL without exposing the database to the public internet.

### Prerequisites

Before enabling Private IP, ensure:
1. A VPC network exists in the same project
2. Private Services Access is configured (see Section 2)
3. The Cloud SQL instance supports private IP (some legacy instances may not)

### Enable Private IP Command

**Note: Execute only with user consent**

```bash
gcloud sql instances patch {{CLOUDSQL_INSTANCE_NAME}} \
  --network=projects/{{PROJECT_ID}}/global/networks/{{VPC_NAME}} \
  --no-assign-ip
```

**To enable both Private and Public IP:**
```bash
gcloud sql instances patch {{CLOUDSQL_INSTANCE_NAME}} \
  --network=projects/{{PROJECT_ID}}/global/networks/{{VPC_NAME}}
```

### Verification

Check that Private IP has been assigned:
```bash
gcloud sql instances describe {{CLOUDSQL_INSTANCE_NAME}} \
  --format="get(ipAddresses)"
```

Expected output should include an entry with `type: PRIVATE`.

**Verification checklist:**
- ✅ Private IP address is listed
- ✅ IP address is in the expected VPC range
- ✅ Instance shows `settings.ipConfiguration.privateNetwork` set to your VPC

---

## 2. Private Services Access Setup

Private Services Access creates a VPC peering connection between your VPC and Google's service producer network, enabling private connectivity to Cloud SQL.

### Step 1: Allocate IP Range for Private Services

**Note: Execute only with user consent**

```bash
gcloud compute addresses create google-managed-services-{{VPC_NAME}} \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network={{VPC_NAME}} \
  --project={{PROJECT_ID}}
```

**Options:**
- Use `--prefix-length=20` for smaller IP range (4,096 addresses)
- Use `--prefix-length=16` for standard range (65,536 addresses)
- Use `--addresses={{IP_RANGE}}` to specify exact range (e.g., `10.1.0.0`)

### Step 2: Create Peering Connection

```bash
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-{{VPC_NAME}} \
  --network={{VPC_NAME}} \
  --project={{PROJECT_ID}}
```

### Verification

Check that Private Services Access is properly configured:

```bash
gcloud services vpc-peerings list \
  --network={{VPC_NAME}} \
  --project={{PROJECT_ID}}
```

Expected output should show:
- `service: servicenetworking.googleapis.com`
- `network: {{VPC_NAME}}`
- Allocated IP ranges

**Alternative verification:**
```bash
gcloud compute addresses list \
  --filter="purpose=VPC_PEERING AND network:{{VPC_NAME}}" \
  --format="table(name,address,prefixLength,network.basename())"
```

---

## 3. VPC Peering Configuration

VPC Peering is needed when your compute resources are in a different VPC than your Cloud SQL instance.

### When VPC Peering is Needed

Use VPC Peering when:
- GCE VM is in VPC-A, Cloud SQL is in VPC-B
- GKE cluster is in a different VPC than Cloud SQL
- Multi-VPC architecture requiring database access across VPCs

### Create VPC Peering Between Two VPCs

**Note: Execute only with user consent**

**Peer from VPC-A to VPC-B:**
```bash
gcloud compute networks peerings create {{PEERING_NAME_A_TO_B}} \
  --network={{VPC_A_NAME}} \
  --peer-project={{PROJECT_ID}} \
  --peer-network={{VPC_B_NAME}} \
  --auto-create-routes
```

**Peer from VPC-B to VPC-A (bidirectional):**
```bash
gcloud compute networks peerings create {{PEERING_NAME_B_TO_A}} \
  --network={{VPC_B_NAME}} \
  --peer-project={{PROJECT_ID}} \
  --peer-network={{VPC_A_NAME}} \
  --auto-create-routes
```

**For cross-project peering:**
```bash
gcloud compute networks peerings create {{PEERING_NAME}} \
  --network={{VPC_NAME}} \
  --peer-project={{PEER_PROJECT_ID}} \
  --peer-network={{PEER_VPC_NAME}} \
  --auto-create-routes
```

### Verification

List all VPC peering connections:
```bash
gcloud compute networks peerings list \
  --network={{VPC_NAME}}
```

Check peering status:
```bash
gcloud compute networks peerings describe {{PEERING_NAME}} \
  --network={{VPC_NAME}} \
  --format="get(state,stateDetails)"
```

Expected status: `ACTIVE`

---

## 4. Firewall Rules

Firewall rules control egress traffic from your compute resources to Cloud SQL.

### Check Existing Firewall Rules

View all firewall rules for a VPC:
```bash
gcloud compute firewall-rules list \
  --filter="network:{{VPC_NAME}}" \
  --format="table(name,direction,priority,allowed,targetTags)"
```

View egress rules specifically:
```bash
gcloud compute firewall-rules list \
  --filter="network:{{VPC_NAME}} AND direction=EGRESS" \
  --format="table(name,direction,allowed,destinationRanges,targetTags)"
```

### Create Egress Rule for PostgreSQL (Port 5432)

**Note: Execute only with user consent**

```bash
gcloud compute firewall-rules create allow-egress-cloudsql-postgres \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432 \
  --destination-ranges={{CLOUDSQL_PRIVATE_IP}}/32 \
  --priority=1000
```

**For entire Cloud SQL IP range:**
```bash
gcloud compute firewall-rules create allow-egress-cloudsql-postgres \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432 \
  --destination-ranges={{PRIVATE_SERVICES_IP_RANGE}} \
  --priority=1000
```

### Create Egress Rule for MySQL (Port 3306)

```bash
gcloud compute firewall-rules create allow-egress-cloudsql-mysql \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:3306 \
  --destination-ranges={{CLOUDSQL_PRIVATE_IP}}/32 \
  --priority=1000
```

### Create Egress Rule for SQL Server (Port 1433)

```bash
gcloud compute firewall-rules create allow-egress-cloudsql-sqlserver \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:1433 \
  --destination-ranges={{CLOUDSQL_PRIVATE_IP}}/32 \
  --priority=1000
```

### Create Egress Rule for All Cloud SQL Ports

```bash
gcloud compute firewall-rules create allow-egress-cloudsql-all \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432,tcp:3306,tcp:1433 \
  --destination-ranges={{PRIVATE_SERVICES_IP_RANGE}} \
  --priority=1000
```

### With Target Tags (Specific VMs/Instances)

```bash
gcloud compute firewall-rules create allow-egress-cloudsql-postgres-tagged \
  --network={{VPC_NAME}} \
  --direction=EGRESS \
  --action=ALLOW \
  --rules=tcp:5432 \
  --destination-ranges={{CLOUDSQL_PRIVATE_IP}}/32 \
  --target-tags={{TAG_NAME}} \
  --priority=1000
```

### Verification

Check if the firewall rule was created:
```bash
gcloud compute firewall-rules describe {{FIREWALL_RULE_NAME}}
```

Test connectivity from a compute instance:
```bash
# PostgreSQL
nc -zv {{CLOUDSQL_PRIVATE_IP}} 5432

# MySQL
nc -zv {{CLOUDSQL_PRIVATE_IP}} 3306

# SQL Server
nc -zv {{CLOUDSQL_PRIVATE_IP}} 1433
```

---

## 5. IAM Permissions

IAM permissions control who and what can access Cloud SQL instances.

### Required Roles for Cloud SQL Access

| Role | Purpose | Permissions |
|------|---------|-------------|
| `roles/cloudsql.client` | Connect to Cloud SQL | Minimal permissions for connections |
| `roles/cloudsql.editor` | Manage and connect | Full instance management |
| `roles/cloudsql.admin` | Full administrative access | All Cloud SQL operations |

### Grant Cloud SQL Client Role to User

**Note: Execute only with user consent**

```bash
gcloud projects add-iam-policy-binding {{PROJECT_ID}} \
  --member="user:{{USER_EMAIL}}" \
  --role="roles/cloudsql.client"
```

### Grant Cloud SQL Client Role to Service Account

```bash
gcloud projects add-iam-policy-binding {{PROJECT_ID}} \
  --member="serviceAccount:{{SERVICE_ACCOUNT_EMAIL}}" \
  --role="roles/cloudsql.client"
```

### Grant Cloud SQL Editor Role

```bash
gcloud projects add-iam-policy-binding {{PROJECT_ID}} \
  --member="user:{{USER_EMAIL}}" \
  --role="roles/cloudsql.editor"
```

### Grant at Instance Level (More Restrictive)

```bash
gcloud sql instances add-iam-policy-binding {{CLOUDSQL_INSTANCE_NAME}} \
  --member="user:{{USER_EMAIL}}" \
  --role="roles/cloudsql.client"
```

### Create Service Account for Cloud SQL Access

```bash
# Create service account
gcloud iam service-accounts create {{SA_NAME}} \
  --display-name="{{DISPLAY_NAME}}" \
  --project={{PROJECT_ID}}

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding {{PROJECT_ID}} \
  --member="serviceAccount:{{SA_NAME}}@{{PROJECT_ID}}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Verification

Check user's IAM permissions:
```bash
gcloud projects get-iam-policy {{PROJECT_ID}} \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:{{USER_EMAIL}}" \
  --format="table(bindings.role)"
```

Check service account's IAM permissions:
```bash
gcloud projects get-iam-policy {{PROJECT_ID}} \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:{{SERVICE_ACCOUNT_EMAIL}}" \
  --format="table(bindings.role)"
```

Check if specific role is granted:
```bash
gcloud projects get-iam-policy {{PROJECT_ID}} \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/cloudsql.client AND bindings.members:user:{{USER_EMAIL}}" \
  --format="value(bindings.role)"
```

---

## 6. Workload Identity Setup (GKE Specific)

Workload Identity allows GKE pods to authenticate as Google Cloud service accounts without needing to manage service account keys.

### Prerequisites

- GKE cluster version 1.12 or later
- Cluster should be VPC-native

### Step 1: Enable Workload Identity on Cluster

**Note: Execute only with user consent**

**For new clusters:**
```bash
gcloud container clusters create {{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --workload-pool={{PROJECT_ID}}.svc.id.goog \
  --enable-ip-alias
```

**For existing clusters:**
```bash
gcloud container clusters update {{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --workload-pool={{PROJECT_ID}}.svc.id.goog
```

### Step 2: Update Node Pool for Workload Identity

```bash
gcloud container node-pools update {{NODE_POOL_NAME}} \
  --cluster={{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --workload-metadata=GKE_METADATA
```

**For default node pool:**
```bash
gcloud container node-pools update default-pool \
  --cluster={{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --workload-metadata=GKE_METADATA
```

### Step 3: Create Google Cloud Service Account

```bash
gcloud iam service-accounts create {{GCP_SA_NAME}} \
  --display-name="{{DISPLAY_NAME}}" \
  --project={{PROJECT_ID}}
```

### Step 4: Grant Cloud SQL Client Role

```bash
gcloud projects add-iam-policy-binding {{PROJECT_ID}} \
  --member="serviceAccount:{{GCP_SA_NAME}}@{{PROJECT_ID}}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### Step 5: Create Kubernetes Service Account

Get cluster credentials first:
```bash
gcloud container clusters get-credentials {{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}}
```

Create the Kubernetes service account:
```bash
kubectl create serviceaccount {{K8S_SA_NAME}} \
  --namespace={{NAMESPACE}}
```

### Step 6: Bind Kubernetes SA to GCP SA

```bash
gcloud iam service-accounts add-iam-policy-binding \
  {{GCP_SA_NAME}}@{{PROJECT_ID}}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:{{PROJECT_ID}}.svc.id.goog[{{NAMESPACE}}/{{K8S_SA_NAME}}]"
```

### Step 7: Annotate Kubernetes Service Account

```bash
kubectl annotate serviceaccount {{K8S_SA_NAME}} \
  --namespace={{NAMESPACE}} \
  iam.gke.io/gcp-service-account={{GCP_SA_NAME}}@{{PROJECT_ID}}.iam.gserviceaccount.com
```

### Verification

Check cluster Workload Identity configuration:
```bash
gcloud container clusters describe {{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --format="get(workloadIdentityConfig.workloadPool)"
```

Expected: `{{PROJECT_ID}}.svc.id.goog`

Check node pool configuration:
```bash
gcloud container node-pools describe {{NODE_POOL_NAME}} \
  --cluster={{CLUSTER_NAME}} \
  --location={{CLUSTER_LOCATION}} \
  --format="get(config.workloadMetadataConfig.mode)"
```

Expected: `GKE_METADATA`

Verify Kubernetes service account annotation:
```bash
kubectl get serviceaccount {{K8S_SA_NAME}} \
  --namespace={{NAMESPACE}} \
  -o yaml
```

Verify IAM binding:
```bash
gcloud iam service-accounts get-iam-policy \
  {{GCP_SA_NAME}}@{{PROJECT_ID}}.iam.gserviceaccount.com \
  --format=json
```

Test from a pod using the service account:
```bash
kubectl run test-wi \
  --image=google/cloud-sdk:slim \
  --serviceaccount={{K8S_SA_NAME}} \
  --namespace={{NAMESPACE}} \
  --rm -it --restart=Never -- gcloud auth list
```

---

## 7. Cloud SQL Auth Proxy Installation

The Cloud SQL Auth Proxy provides secure access to Cloud SQL instances without requiring allowlisted IP addresses.

### macOS (Apple Silicon - M1/M2/M3/M4)

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.arm64
chmod +x cloud-sql-proxy
```

**Optional: Move to PATH:**
```bash
sudo mv cloud-sql-proxy /usr/local/bin/
```

### macOS (Intel x86_64)

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy
```

**Optional: Move to PATH:**
```bash
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Linux (amd64)

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
```

**Optional: Move to PATH:**
```bash
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Linux (arm64)

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.arm64
chmod +x cloud-sql-proxy
```

**Optional: Move to PATH:**
```bash
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.x64.exe" -OutFile "cloud-sql-proxy.exe"
```

**Optional: Add to PATH or move to a directory in PATH**

### Basic Usage

**PostgreSQL (default port 5432):**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --port=5432
```

**MySQL (default port 3306):**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --port=3306
```

**SQL Server (default port 1433):**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --port=1433
```

**Custom port:**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --port={{CUSTOM_PORT}}
```

**Multiple instances:**
```bash
./cloud-sql-proxy {{CONNECTION_NAME_1}} {{CONNECTION_NAME_2}}
```

**With IAM authentication:**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --auto-iam-authn
```

**Run in background (Unix):**
```bash
nohup ./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} --port=5432 &
```

**With specific credentials:**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} \
  --credentials-file={{PATH_TO_KEY_JSON}}
```

**Advanced options:**
```bash
./cloud-sql-proxy {{CLOUDSQL_CONNECTION_NAME}} \
  --port=5432 \
  --structured-logs \
  --max-connections=10
```

### Verification

Check if Auth Proxy is running:
```bash
ps aux | grep cloud-sql-proxy
```

Test connection (PostgreSQL):
```bash
psql "host=127.0.0.1 port=5432 user={{DB_USER}} dbname={{DB_NAME}}"
```

Test connection (MySQL):
```bash
mysql -h 127.0.0.1 -P 3306 -u {{DB_USER}} -p {{DB_NAME}}
```

Test connection (SQL Server):
```bash
sqlcmd -S 127.0.0.1,1433 -U {{DB_USER}} -P {{DB_PASSWORD}} -d {{DB_NAME}}
```

Check Auth Proxy logs for connection status - it will display:
```
Ready for new connections
Listening on 127.0.0.1:5432
```

---

## Usage Notes

1. **Variable Substitution**: Replace all `{{PLACEHOLDER}}` values with actual values from your environment
2. **Consent Required**: All remediation commands should only be executed after obtaining user consent
3. **Order of Operations**: Some remediation steps have dependencies (e.g., Private Services Access must exist before enabling Private IP)
4. **Verification**: Always run verification commands after remediation to confirm successful configuration
5. **Regional Resources**: Ensure region/zone parameters match your resource locations
6. **Idempotency**: Most commands can be safely re-run; they will update existing configurations or report if already configured

---

## Common Troubleshooting

### Private IP Not Connecting
1. Verify Private Services Access is configured (Section 2)
2. Check VPC peering status is ACTIVE (Section 3)
3. Verify firewall rules allow egress (Section 4)
4. Ensure compute and Cloud SQL are in same/peered VPC

### IAM Permission Denied
1. Check user/SA has correct role (Section 5)
2. Verify role binding at project or instance level
3. Wait up to 2 minutes for IAM changes to propagate

### Workload Identity Not Working
1. Verify cluster and node pool configuration (Section 6)
2. Check annotation on Kubernetes SA
3. Confirm GCP SA has workloadIdentityUser role
4. Verify namespace matches in binding

### Auth Proxy Connection Failed
1. Check Auth Proxy is running (Section 7)
2. Verify connection name format: `project:region:instance`
3. Confirm IAM permissions (need cloudsql.client role)
4. Check Application Default Credentials are set
