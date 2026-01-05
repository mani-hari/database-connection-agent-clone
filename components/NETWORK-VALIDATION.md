# Network Validation Component

This component documents the shared network validation logic used across all compute types (GCE VM, GKE, Cloud Run, Local IDE) when connecting to Cloud SQL.

---

## 1. Cloud SQL Instance Analysis

### 1.1 Describe Cloud SQL Instance

**Command:**
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,settings.ipConfiguration.authorizedNetworks,region)"
```

**Purpose:** Retrieve comprehensive Cloud SQL instance configuration including network settings.

### 1.2 Fields to Extract

Extract and store the following from the command output:

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `CLOUDSQL_CONNECTION_NAME` | `connectionName` | Full connection identifier | `my-project:us-central1:my-instance` |
| `CLOUDSQL_PRIVATE_IP` | `ipAddresses[type=PRIVATE].ipAddress` | Private IP address if enabled | `10.1.2.3` |
| `CLOUDSQL_PUBLIC_IP` | `ipAddresses[type=PRIMARY].ipAddress` | Public IP address if enabled | `34.123.45.67` |
| `CLOUDSQL_VPC` | `settings.ipConfiguration.privateNetwork` | VPC network path if private IP enabled | `projects/my-project/global/networks/default` |
| `CLOUDSQL_REGION` | `region` | Cloud SQL region | `us-central1` |

### 1.3 IP Address Parsing

**Private IP Check:**
```bash
# Extract private IP
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIVATE).ipAddress)"
```

**Public IP Check:**
```bash
# Extract public IP
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIMARY).ipAddress)"
```

**VPC Network:**
```bash
# Extract VPC network
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(settings.ipConfiguration.privateNetwork)"
```

---

## 2. Common Network Checks

### 2.1 Private IP Enabled Check

**Check:** Does the Cloud SQL instance have a private IP address?

```bash
CLOUDSQL_PRIVATE_IP=$(gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIVATE).ipAddress)")

if [ -z "$CLOUDSQL_PRIVATE_IP" ]; then
  echo "❌ Private IP: Not enabled"
else
  echo "✅ Private IP: $CLOUDSQL_PRIVATE_IP"
fi
```

**Implications:**
- **Enabled:** Can use private connectivity if on same VPC
- **Not Enabled:** Must use public IP or enable private IP

### 2.2 Public IP Availability

**Check:** Does the Cloud SQL instance have a public IP address?

```bash
CLOUDSQL_PUBLIC_IP=$(gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIMARY).ipAddress)")

if [ -z "$CLOUDSQL_PUBLIC_IP" ]; then
  echo "❌ Public IP: Not enabled"
else
  echo "✅ Public IP: $CLOUDSQL_PUBLIC_IP"
fi
```

**Implications:**
- **Enabled:** Can use Auth Proxy with public IP (less secure)
- **Not Enabled:** Must use private IP connectivity

### 2.3 VPC Network Alignment

**Check:** Are the compute resource and Cloud SQL in the same VPC?

This check varies by compute type:

**For GCE VM:**
```bash
VM_VPC=$(gcloud compute instances describe VM_NAME --zone=VM_ZONE --format="value(networkInterfaces[0].network)")
CLOUDSQL_VPC=$(gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(settings.ipConfiguration.privateNetwork)")

if [ "$VM_VPC" = "$CLOUDSQL_VPC" ]; then
  echo "✅ Same VPC Network: $VM_VPC"
else
  echo "❌ Different VPC: VM=$VM_VPC, Cloud SQL=$CLOUDSQL_VPC"
fi
```

**For GKE:**
```bash
GKE_VPC=$(gcloud container clusters describe GKE_CLUSTER_NAME --location=GKE_CLUSTER_LOCATION --format="value(network)")
CLOUDSQL_VPC=$(gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="value(settings.ipConfiguration.privateNetwork)")

if [[ "$GKE_VPC" == *"$CLOUDSQL_VPC"* ]]; then
  echo "✅ Same VPC Network"
else
  echo "❌ Different VPC"
fi
```

### 2.4 Private Services Access Status

**Check:** Is Private Services Access configured for the VPC?

```bash
VPC_NAME="default"  # Extract from CLOUDSQL_VPC path

gcloud services vpc-peerings list --network=$VPC_NAME --project=PROJECT_ID --format="table(network,service,peering)"
```

**Look for:**
- Service: `servicenetworking.googleapis.com`
- Peering status should be active

**If not configured:**
```bash
# Step 1: Allocate IP range
gcloud compute addresses create google-managed-services-$VPC_NAME \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=$VPC_NAME \
  --project=PROJECT_ID

# Step 2: Create peering connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-$VPC_NAME \
  --network=$VPC_NAME \
  --project=PROJECT_ID
```

---

## 3. Decision Tree Logic

### 3.1 Connection Method Decision Flow

```
START: Analyze Cloud SQL and Compute Configuration
│
├─ Has Private IP?
│  ├─ YES
│  │  └─ Same VPC as compute resource?
│  │     ├─ YES
│  │     │  └─ ✅ RECOMMEND: Direct Private IP Connection
│  │     │     - Most secure and performant
│  │     │     - No additional proxy needed (for GCE VM)
│  │     │     - Use Auth Proxy sidecar (for GKE)
│  │     │     - Use built-in connection or VPC Connector (for Cloud Run)
│  │     │
│  │     └─ NO (Different VPC)
│  │        └─ ⚠️ RECOMMEND: VPC Peering or Auth Proxy
│  │           - VPC Peering: Connect the two VPCs
│  │           - OR use Auth Proxy with private IP
│  │           - OR move Cloud SQL to compute VPC
│  │
│  └─ NO (No Private IP)
│     └─ Has Public IP?
│        ├─ YES
│        │  └─ ⚠️ RECOMMEND: Auth Proxy with Public IP
│        │     - Less secure than private IP
│        │     - Auth Proxy provides encryption
│        │     - Consider enabling Private IP instead
│        │
│        └─ NO
│           └─ ❌ RECOMMEND: Enable Private IP or Public IP
│              - Enable Private IP (preferred)
│              - OR enable Public IP temporarily
```

### 3.2 Connection Method Recommendations by Scenario

| Scenario | Private IP | Public IP | Same VPC | Recommendation |
|----------|-----------|-----------|----------|----------------|
| 1 | ✅ | ✅ | ✅ | **Private IP** (most secure) |
| 2 | ✅ | ✅ | ❌ | **VPC Peering** or **Auth Proxy** |
| 3 | ✅ | ❌ | ✅ | **Private IP** (only option) |
| 4 | ✅ | ❌ | ❌ | **VPC Peering** required |
| 5 | ❌ | ✅ | N/A | **Auth Proxy** with Public IP |
| 6 | ❌ | ❌ | N/A | **Enable Private or Public IP** |

### 3.3 Remediation Commands

**Enable Private IP on Cloud SQL:**
```bash
gcloud sql instances patch CLOUDSQL_INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/VPC_NAME \
  --no-assign-ip
```
**Note:** This requires downtime and Private Services Access to be configured.

**Enable Public IP on Cloud SQL:**
```bash
gcloud sql instances patch CLOUDSQL_INSTANCE_NAME \
  --assign-ip
```

**Add Authorized Network (for Public IP):**
```bash
gcloud sql instances patch CLOUDSQL_INSTANCE_NAME \
  --authorized-networks=EXTERNAL_IP/32
```

---

## 4. Compute-Specific Checks

### 4.1 GCE VM Network Validation

#### 4.1.1 Gather VM Network Details

```bash
gcloud compute instances describe VM_NAME --zone=VM_ZONE --format="yaml(name,networkInterfaces[].network,networkInterfaces[].networkIP,networkInterfaces[].accessConfigs[].natIP,networkInterfaces[].subnetwork)"
```

**Extract:**
- `VM_INTERNAL_IP`: Internal IP address within VPC
- `VM_EXTERNAL_IP`: External/public IP (may be null)
- `VM_VPC`: VPC network path
- `VM_SUBNET`: Subnet path

#### 4.1.2 VPC Comparison

```bash
# Compare VPC networks
if [ "$VM_VPC" = "$CLOUDSQL_VPC" ]; then
  echo "✅ Same VPC Network"
  SAME_VPC=true
else
  echo "❌ Different VPC Networks"
  echo "   VM VPC: $VM_VPC"
  echo "   Cloud SQL VPC: $CLOUDSQL_VPC"
  SAME_VPC=false
fi
```

#### 4.1.3 Firewall Rules Check

```bash
# Check egress firewall rules for Cloud SQL ports
gcloud compute firewall-rules list \
  --filter="network:$VPC_NAME AND direction=EGRESS" \
  --format="table(name,direction,allowed,targetTags)"
```

**Required egress rules:**
- PostgreSQL: TCP port 5432
- MySQL: TCP port 3306
- SQL Server: TCP port 1433

#### 4.1.4 Network Analysis Output (GCE)

```
╔══════════════════════════════════════════════════════════════════╗
║                    NETWORK ANALYSIS RESULTS                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ GCE VM: [VM_NAME]                                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅ / ❌  │ [IP or "Not enabled"] ║
║ Cloud SQL Public IP            │ ✅ / ❌  │ [IP or "Not enabled"] ║
║ VM Internal IP                 │ ✅ / ❌  │ [IP]                  ║
║ VM External IP                 │ ✅ / ❌  │ [IP or "None"]        ║
║ Same VPC Network               │ ✅ / ❌  │ [VPC names]           ║
║ Private Services Access        │ ✅ / ❌  │ [Status]              ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED CONNECTION METHOD: [Private IP / Public IP / Proxy]  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

### 4.2 GKE Network Validation

#### 4.2.1 Gather GKE Cluster Details

```bash
gcloud container clusters describe GKE_CLUSTER_NAME --location=GKE_CLUSTER_LOCATION --format="yaml(name,network,subnetwork,privateClusterConfig,workloadIdentityConfig,ipAllocationPolicy)"
```

**Extract:**
- `GKE_VPC`: Cluster VPC network
- `GKE_SUBNET`: Cluster subnet
- `WORKLOAD_IDENTITY_ENABLED`: Boolean, true if workloadIdentityConfig.workloadPool exists
- `WORKLOAD_POOL`: Format `PROJECT_ID.svc.id.goog`
- `VPC_NATIVE`: Boolean, true if ipAllocationPolicy.useIpAliases is true
- `PRIVATE_CLUSTER`: Boolean, true if privateClusterConfig.enablePrivateNodes is true

#### 4.2.2 Workload Identity Check

```bash
gcloud container clusters describe GKE_CLUSTER_NAME \
  --location=GKE_CLUSTER_LOCATION \
  --format="value(workloadIdentityConfig.workloadPool)"
```

**If output exists:**
```
✅ Workload Identity: Enabled
   Pool: PROJECT_ID.svc.id.goog
```

**If empty:**
```
❌ Workload Identity: Not enabled
   Recommend: Enable for secure authentication without service account keys
```

#### 4.2.3 Private Google Access Check

```bash
# Extract subnet region from GKE_SUBNET
SUBNET_REGION=$(echo $GKE_SUBNET | cut -d'/' -f9)

gcloud compute networks subnets describe $GKE_SUBNET \
  --region=$SUBNET_REGION \
  --format="value(privateIpGoogleAccess)"
```

**Enable if needed:**
```bash
gcloud compute networks subnets update $GKE_SUBNET \
  --region=$SUBNET_REGION \
  --enable-private-ip-google-access
```

#### 4.2.4 VPC-Native Mode Check

```bash
VPC_NATIVE=$(gcloud container clusters describe GKE_CLUSTER_NAME \
  --location=GKE_CLUSTER_LOCATION \
  --format="value(ipAllocationPolicy.useIpAliases)")

if [ "$VPC_NATIVE" = "True" ]; then
  echo "✅ VPC-Native Mode: Enabled"
else
  echo "❌ VPC-Native Mode: Disabled"
  echo "   Routes-based clusters not recommended for Cloud SQL"
fi
```

#### 4.2.5 Network Analysis Output (GKE)

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

#### 4.2.6 GKE-Specific Recommendations

**If Workload Identity enabled AND same VPC:**
- ✅ **Recommended:** Auth Proxy sidecar with Workload Identity
- Most secure, no secrets in cluster
- Automatic credential rotation

**If Workload Identity NOT enabled:**
- ⚠️ **Recommend:** Enable Workload Identity
- Alternative: Use service account key (less secure)

**If different VPC:**
- ⚠️ **Recommend:** VPC Peering or move Cloud SQL to GKE VPC

---

### 4.3 Cloud Run Network Validation

#### 4.3.1 Cloud Run Connection Options

Cloud Run has three connection methods:

| Option | Method | Use Case |
|--------|--------|----------|
| 1 | Built-in Cloud SQL (Unix Socket) | Simplest, recommended for most cases |
| 2 | Private IP via VPC Connector | When you need direct VPC access |
| 3 | Direct VPC Egress | High throughput, no connector overhead |

#### 4.3.2 Check Existing Service Configuration

```bash
gcloud run services describe CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --format="yaml(spec.template.metadata.annotations,spec.template.spec.serviceAccountName)"
```

**Look for:**
- `run.googleapis.com/cloudsql-instances`: Existing Cloud SQL connections
- `run.googleapis.com/vpc-access-connector`: VPC connector configuration
- `serviceAccountName`: Service account for authentication

#### 4.3.3 VPC Connector Check

```bash
# List VPC connectors in region
gcloud compute networks vpc-access connectors list \
  --region=CLOUDRUN_REGION \
  --format="table(name,network,ipCidrRange,state)"
```

**If none exist and needed:**
```bash
gcloud compute networks vpc-access connectors create cloudrun-connector \
  --region=CLOUDRUN_REGION \
  --network=VPC_NAME \
  --range=10.8.0.0/28
```

#### 4.3.4 Network Analysis Output (Cloud Run)

```
╔══════════════════════════════════════════════════════════════════╗
║                 CLOUD RUN CONNECTION OPTIONS                      ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ Connection Name: [CLOUDSQL_CONNECTION_NAME]                       ║
╠══════════════════════════════════════════════════════════════════╣
║ OPTION │ METHOD                    │ BEST FOR                    ║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   1    │ Built-in Cloud SQL        │ Simplest setup, recommended ║
║        │ (Unix Socket)             │ No VPC configuration needed ║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   2    │ Private IP via VPC        │ When you need private IP    ║
║        │ Connector                 │ Higher security requirements║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   3    │ Direct VPC Egress         │ High throughput needs       ║
║        │ (Private IP)              │ No connector overhead       ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: Option 1 (Built-in Cloud SQL Connection)            ║
╚══════════════════════════════════════════════════════════════════╝
```

#### 4.3.5 Cloud Run Decision Logic

```
Cloud Run Connection Method Selection:
│
├─ Default Case
│  └─ ✅ RECOMMEND: Built-in Cloud SQL (Unix Socket)
│     - Uses connection annotation: --add-cloudsql-instances
│     - No VPC configuration needed
│     - Works with both private and public IPs
│
├─ Need Direct VPC Access?
│  └─ Option 2: VPC Connector
│     - Create VPC connector in same region
│     - Configure: --vpc-connector=cloudrun-connector
│     - Use private IP for connection
│
└─ Need High Performance / Low Latency?
   └─ Option 3: Direct VPC Egress
      - Configure: --network and --subnet
      - Use private IP for connection
      - No connector overhead
```

---

### 4.4 Local IDE Network Validation

#### 4.4.1 Application Default Credentials Check

```bash
gcloud auth application-default print-access-token
```

**If successful:**
```
✅ Application Default Credentials: Configured
   Account: user@example.com
```

**If failed:**
```
❌ Application Default Credentials: Not configured

Run this command:
gcloud auth application-default login
```

#### 4.4.2 Cloud SQL Admin API Check

```bash
gcloud services list \
  --enabled \
  --filter="name:sqladmin.googleapis.com" \
  --format="value(name)"
```

**If output is empty:**
```bash
gcloud services enable sqladmin.googleapis.com
```

**Verification:**
```
✅ Cloud SQL Admin API: Enabled
```

#### 4.4.3 IAM Permissions Check

```bash
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:USER_EMAIL" \
  --format="table(bindings.role)"
```

**Required roles:**
- `roles/cloudsql.client` (minimum)
- OR `roles/cloudsql.editor`
- OR `roles/cloudsql.admin`

**If missing:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:USER_EMAIL" \
  --role="roles/cloudsql.client"
```

#### 4.4.4 Network Analysis Output (Local IDE)

```
╔══════════════════════════════════════════════════════════════════╗
║                    LOCAL CONNECTION ANALYSIS                      ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ Connection Name: [CLOUDSQL_CONNECTION_NAME]                       ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Admin API            │ ✅ / ❌  │ [Enabled/Disabled]    ║
║ Application Default Creds      │ ✅ / ❌  │ [Account email]       ║
║ IAM Permissions                │ ✅ / ❌  │ [cloudsql.client]     ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: Cloud SQL Auth Proxy on localhost:PORT              ║
╚══════════════════════════════════════════════════════════════════╝
```

#### 4.4.5 Local IDE Recommendation

**Always recommend:**
- ✅ Cloud SQL Auth Proxy running locally
- Connection via localhost (127.0.0.1)
- No VPC network considerations (proxy handles secure tunnel)

**Alternative:**
- Cloud SQL Connector libraries (embedded in application)
- No separate proxy process needed

---

## 5. Summary Table: Validation Checks by Compute Type

| Check | GCE VM | GKE | Cloud Run | Local IDE |
|-------|--------|-----|-----------|-----------|
| Cloud SQL Private IP | ✅ | ✅ | ✅ | N/A |
| Cloud SQL Public IP | ✅ | ✅ | ✅ | N/A |
| VPC Network Match | ✅ | ✅ | ⚠️ Optional | N/A |
| Private Services Access | ✅ | ✅ | ⚠️ Optional | N/A |
| Firewall Rules | ✅ | ⚠️ Optional | N/A | N/A |
| Workload Identity | N/A | ✅ | N/A | N/A |
| Private Google Access | N/A | ✅ | N/A | N/A |
| VPC-Native Mode | N/A | ✅ | N/A | N/A |
| VPC Connector | N/A | N/A | ⚠️ Optional | N/A |
| ADC Credentials | N/A | N/A | N/A | ✅ |
| Cloud SQL Admin API | N/A | N/A | N/A | ✅ |
| IAM Permissions | ✅ | ✅ | ✅ | ✅ |

**Legend:**
- ✅ = Required check
- ⚠️ = Optional/conditional check
- N/A = Not applicable

---

## 6. ASCII Card Format Template

All network analysis outputs should follow this consistent format:

```
╔══════════════════════════════════════════════════════════════════╗
║                    [ANALYSIS TYPE] RESULTS                        ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ Compute Resource: [RESOURCE_NAME]                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ [Check 1]                      │ ✅ / ❌  │ [Details]             ║
║ [Check 2]                      │ ✅ / ❌  │ [Details]             ║
║ [Check 3]                      │ ✅ / ❌  │ [Details]             ║
║ [Check 4]                      │ ✅ / ❌  │ [Details]             ║
║ [Check 5]                      │ ✅ / ❌  │ [Details]             ║
║ [Check 6]                      │ ✅ / ❌  │ [Details]             ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED CONNECTION METHOD: [Method Description]              ║
╚══════════════════════════════════════════════════════════════════╝
```

**Status Indicators:**
- ✅ = Check passed / Feature enabled
- ❌ = Check failed / Feature disabled
- ⚠️ = Warning / Attention needed

---

## 7. Complete Validation Workflow

### 7.1 Standard Validation Sequence

```bash
#!/bin/bash
# Complete network validation workflow

# Step 1: Gather Cloud SQL details
echo "Step 1: Analyzing Cloud SQL instance..."
gcloud sql instances describe $CLOUDSQL_INSTANCE_NAME \
  --format="yaml(connectionName,ipAddresses,settings.ipConfiguration.privateNetwork)"

# Step 2: Extract network configuration
CLOUDSQL_CONNECTION_NAME=$(gcloud sql instances describe $CLOUDSQL_INSTANCE_NAME --format="value(connectionName)")
CLOUDSQL_PRIVATE_IP=$(gcloud sql instances describe $CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIVATE).ipAddress)")
CLOUDSQL_PUBLIC_IP=$(gcloud sql instances describe $CLOUDSQL_INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIMARY).ipAddress)")
CLOUDSQL_VPC=$(gcloud sql instances describe $CLOUDSQL_INSTANCE_NAME --format="value(settings.ipConfiguration.privateNetwork)")

# Step 3: Gather compute resource details (example for GCE)
echo "Step 2: Analyzing compute resource..."
VM_VPC=$(gcloud compute instances describe $VM_NAME --zone=$VM_ZONE --format="value(networkInterfaces[0].network)")

# Step 4: Compare and analyze
echo "Step 3: Network validation..."
if [ -n "$CLOUDSQL_PRIVATE_IP" ] && [ "$VM_VPC" = "$CLOUDSQL_VPC" ]; then
  echo "✅ Optimal: Private IP connection available"
  RECOMMENDED_METHOD="Private IP"
elif [ -n "$CLOUDSQL_PRIVATE_IP" ]; then
  echo "⚠️ Warning: Private IP available but different VPC"
  RECOMMENDED_METHOD="VPC Peering or Auth Proxy"
elif [ -n "$CLOUDSQL_PUBLIC_IP" ]; then
  echo "⚠️ Warning: Only public IP available"
  RECOMMENDED_METHOD="Auth Proxy with Public IP"
else
  echo "❌ Error: No connectivity options available"
  RECOMMENDED_METHOD="Enable Private or Public IP"
fi

# Step 5: Display results
cat << EOF
╔══════════════════════════════════════════════════════════════════╗
║                    NETWORK ANALYSIS RESULTS                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Private IP           │ $([ -n "$CLOUDSQL_PRIVATE_IP" ] && echo "✅" || echo "❌")       │ ${CLOUDSQL_PRIVATE_IP:-Not enabled} ║
║ Cloud SQL Public IP            │ $([ -n "$CLOUDSQL_PUBLIC_IP" ] && echo "✅" || echo "❌")       │ ${CLOUDSQL_PUBLIC_IP:-Not enabled}  ║
║ Same VPC Network               │ $([ "$VM_VPC" = "$CLOUDSQL_VPC" ] && echo "✅" || echo "❌")    │ Match status         ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: $RECOMMENDED_METHOD                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
```

---

## 8. Error Handling and Edge Cases

### 8.1 No IP Addresses Configured

**Scenario:** Cloud SQL instance has neither private nor public IP.

**Detection:**
```bash
if [ -z "$CLOUDSQL_PRIVATE_IP" ] && [ -z "$CLOUDSQL_PUBLIC_IP" ]; then
  echo "❌ ERROR: Cloud SQL instance has no IP addresses configured"
fi
```

**Resolution:**
Offer to enable either private or public IP (prefer private).

### 8.2 VPC Network Not Found

**Scenario:** Cloud SQL has private IP but VPC network path is invalid.

**Detection:**
```bash
if [ -n "$CLOUDSQL_PRIVATE_IP" ] && [ -z "$CLOUDSQL_VPC" ]; then
  echo "❌ ERROR: Private IP enabled but VPC network not found"
fi
```

**Resolution:**
Check Cloud SQL configuration for network settings.

### 8.3 Private Services Access Not Configured

**Scenario:** Same VPC but private services access missing.

**Detection:**
```bash
PEERING_STATUS=$(gcloud services vpc-peerings list \
  --network=$VPC_NAME \
  --filter="service:servicenetworking.googleapis.com" \
  --format="value(peering)")

if [ -z "$PEERING_STATUS" ]; then
  echo "❌ Private Services Access not configured"
fi
```

**Resolution:**
Offer to configure private services access (shown in section 2.4).

### 8.4 Workload Identity Not Enabled (GKE)

**Scenario:** GKE cluster without Workload Identity trying to connect to Cloud SQL.

**Detection:**
```bash
if [ -z "$WORKLOAD_POOL" ]; then
  echo "⚠️ WARNING: Workload Identity not enabled"
  echo "   Less secure alternatives required (service account keys)"
fi
```

**Resolution:**
- Recommend enabling Workload Identity
- Provide fallback using service account keys

---

## 9. Best Practices

### 9.1 Security Best Practices

1. **Always prefer Private IP over Public IP**
   - More secure, traffic stays within Google's network
   - No exposure to internet

2. **Enable Workload Identity for GKE**
   - No need to manage service account keys
   - Automatic credential rotation

3. **Use Cloud SQL Auth Proxy when possible**
   - Provides encryption and authentication
   - Automatic connection management

4. **Restrict firewall rules**
   - Only allow necessary ports (3306, 5432, 1433)
   - Use target tags and service accounts for specificity

### 9.2 Performance Best Practices

1. **Same VPC = Best Performance**
   - Lowest latency
   - No additional hops

2. **VPC Peering over Public IP**
   - Better than public internet
   - Private connectivity

3. **Private Google Access for GKE**
   - Required for private clusters
   - Enables access to Google services without external IPs

### 9.3 Cost Optimization

1. **Direct Private IP (GCE VM)**
   - No Auth Proxy needed = lower compute costs
   - Same VPC = no VPC peering charges

2. **Built-in Cloud SQL Connection (Cloud Run)**
   - No VPC connector needed = save on connector costs
   - Simpler configuration

3. **VPC Connector vs Direct VPC Egress (Cloud Run)**
   - Direct VPC Egress: No connector costs, but requires more configuration
   - VPC Connector: Small additional cost, easier setup

---

## 10. Reference Commands Summary

### 10.1 Cloud SQL Commands

```bash
# Describe instance
gcloud sql instances describe INSTANCE_NAME

# Get private IP
gcloud sql instances describe INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIVATE).ipAddress)"

# Get public IP
gcloud sql instances describe INSTANCE_NAME --format="value(ipAddresses.filter(type:PRIMARY).ipAddress)"

# Get VPC network
gcloud sql instances describe INSTANCE_NAME --format="value(settings.ipConfiguration.privateNetwork)"

# Get connection name
gcloud sql instances describe INSTANCE_NAME --format="value(connectionName)"
```

### 10.2 VPC and Network Commands

```bash
# List VPC peerings
gcloud services vpc-peerings list --network=VPC_NAME

# Check private Google access
gcloud compute networks subnets describe SUBNET_NAME --region=REGION --format="value(privateIpGoogleAccess)"

# List firewall rules
gcloud compute firewall-rules list --filter="network:VPC_NAME"

# Check VPC connector
gcloud compute networks vpc-access connectors list --region=REGION
```

### 10.3 Compute Resource Commands

```bash
# GCE VM network details
gcloud compute instances describe VM_NAME --zone=ZONE --format="yaml(networkInterfaces)"

# GKE cluster network details
gcloud container clusters describe CLUSTER_NAME --location=LOCATION --format="yaml(network,workloadIdentityConfig)"

# Cloud Run service details
gcloud run services describe SERVICE_NAME --region=REGION --format="yaml(spec.template)"
```

### 10.4 IAM and Permissions Commands

```bash
# Check IAM policy
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:user:EMAIL"

# Add Cloud SQL client role
gcloud projects add-iam-policy-binding PROJECT_ID --member="user:EMAIL" --role="roles/cloudsql.client"

# Check enabled APIs
gcloud services list --enabled --filter="name:sqladmin.googleapis.com"
```
