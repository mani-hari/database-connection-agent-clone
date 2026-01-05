# GCE VM → Cloud SQL Connection Guide

**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Component References:**
- UI patterns: See `../components/UI-CARDS.md` for ASCII card templates
- Code snippets: See `../components/CODE-SNIPPETS.md` for connection code
- Validation logic: See `../components/NETWORK-VALIDATION.md` for shared checks
- Remediation: See `../components/REMEDIATION.md` for common fix procedures

---

## Step 2A: Fetch and Select GCE VM

### 2A.1 Display Loading Message
```
Fetching GCE instances... please wait
```

### 2A.2 List All VMs
```bash
gcloud compute instances list --format="table(name,zone,machineType.basename(),status)" --sort-by=name
```

### 2A.3 User Selection
Present VMs as numbered list. Accept number or name input. Capture `VM_NAME` and `VM_ZONE`.

Display confirmation:
```
✅ Selected VM: {VM_NAME} in zone {VM_ZONE}
```

**→ Ask: "Ready to proceed to Step 3 (Network Validation)? (yes/no)"**

**Auto-Complete Mode:** If user selected auto-complete in Step 2.1, skip "Ready to proceed?" prompts and continue directly. Still pause for consent before modifying resources.

---

## Step 3A: GCE VM Network Validation

### 3A.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe {CLOUDSQL_INSTANCE_NAME} --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,region)"
```

Extract and store:
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork)
- `CLOUDSQL_CONNECTION_NAME` (from connectionName field)

### 3A.2 Gather GCE VM Details
```bash
gcloud compute instances describe {VM_NAME} --zone={VM_ZONE} --format="yaml(name,networkInterfaces[].network,networkInterfaces[].networkIP)"
```

Extract and store:
- `VM_INTERNAL_IP` (from networkInterfaces[0].networkIP)
- `VM_VPC` (from networkInterfaces[0].network, extract VPC name from full path)

### 3A.3 Network Analysis Output
Display results in this exact format:

```
╔══════════════════════════════════════════════════════════════════╗
║                    NETWORK ANALYSIS RESULTS                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: {CLOUDSQL_INSTANCE_NAME}                     ║
║ GCE VM: {VM_NAME}                                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅ / ❌  │ {IP or "Not enabled"} ║
║ VM Internal IP                 │ ✅       │ {VM_INTERNAL_IP}      ║
║ Same VPC Network               │ ✅ / ❌  │ {VPC comparison}      ║
║ Private Services Access        │ ✅ / ❌  │ {Status}              ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: {Private IP / Public IP with Auth Proxy}            ║
╚══════════════════════════════════════════════════════════════════╝
```

### 3A.4 Connectivity Decision Tree

**If Private IP available AND same VPC:**
- ✅ Direct connection via Private IP (proceed to Step 4)

**If Private IP available BUT different VPC:**
- ⚠️ VPCs don't match - offer remediation (see 3A.5)

**If only Public IP available:**
- ⚠️ Less secure - recommend Cloud SQL Auth Proxy connection

### 3A.5 Remediation Commands (Execute only with user consent)

**If Cloud SQL needs Private IP enabled:**
```bash
gcloud sql instances patch {CLOUDSQL_INSTANCE_NAME} \
  --network={VM_VPC} \
  --no-assign-ip
```
*Note: This requires Private Services Access to be set up (see below).*

**Check Private Services Access:**
```bash
gcloud services vpc-peerings list --network={VM_VPC} --project={PROJECT_ID}
```

**Create Private Services Access (if missing):**
```bash
# Allocate IP range
gcloud compute addresses create google-managed-services-{VM_VPC} \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network={VM_VPC} \
  --project={PROJECT_ID}

# Create peering connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-{VM_VPC} \
  --network={VM_VPC} \
  --project={PROJECT_ID}
```

After remediation, re-run validation (Step 3A.1).

**→ Ask: "Ready to proceed to Step 4 (Connection Testing)? (yes/no)"**

---

## Step 4A: GCE VM Connection Testing and Code

### 4A.1 Connection Summary
Display:
```
CONNECTION SUMMARY
─────────────────────────────────
Method: {Private IP / Public IP with Auth Proxy}
Host: {CLOUDSQL_PRIVATE_IP or "127.0.0.1 via Auth Proxy"}
Port: {3306/5432/1433 based on database type}
Connection Name: {CLOUDSQL_CONNECTION_NAME}
─────────────────────────────────
```

### 4A.2 Quick Connectivity Test (Optional)
Offer to test connectivity from the VM. Determine command based on `CLOUDSQL_DATABASE_VERSION`:

**For PostgreSQL:**
```bash
gcloud compute ssh {VM_NAME} --zone={VM_ZONE} --command="pg_isready -h {CLOUDSQL_PRIVATE_IP} -p 5432"
```

**For MySQL:**
```bash
gcloud compute ssh {VM_NAME} --zone={VM_ZONE} --command="mysqladmin ping -h {CLOUDSQL_PRIVATE_IP} --silent"
```

**For SQL Server:**
```bash
gcloud compute ssh {VM_NAME} --zone={VM_ZONE} --command="nc -zv {CLOUDSQL_PRIVATE_IP} 1433"
```

### 4A.3 Connection Code

Based on `CLOUDSQL_DATABASE_VERSION`, provide the appropriate connection code:

**Python + PostgreSQL:**
```python
import sqlalchemy
import os

def connect_to_cloud_sql():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")
    db_host = "{CLOUDSQL_PRIVATE_IP}"

    pool = sqlalchemy.create_engine(
        f"postgresql+pg8000://{db_user}:{db_pass}@{db_host}:5432/{db_name}",
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool
```

**Python + MySQL:**
```python
import sqlalchemy
import os

def connect_to_cloud_sql():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")
    db_host = "{CLOUDSQL_PRIVATE_IP}"

    pool = sqlalchemy.create_engine(
        f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:3306/{db_name}",
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool
```

**Node.js + PostgreSQL:**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: '{CLOUDSQL_PRIVATE_IP}',
  port: 5432,
  user: process.env.DB_USER || 'your-db-user',
  password: process.env.DB_PASS || 'your-db-password',
  database: process.env.DB_NAME || 'your-database',
  max: 10,
});

module.exports = { pool };
```

**Node.js + MySQL:**
```javascript
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: '{CLOUDSQL_PRIVATE_IP}',
  port: 3306,
  user: process.env.DB_USER || 'your-db-user',
  password: process.env.DB_PASS || 'your-db-password',
  database: process.env.DB_NAME || 'your-database',
  waitForConnections: true,
  connectionLimit: 10,
});

module.exports = { pool };
```

---

## Completion

Display:
```
✅ GCE VM → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: {CLOUDSQL_INSTANCE_NAME}
- GCE VM: {VM_NAME} ({VM_ZONE})
- Connection Method: {Private IP / Public IP with Auth Proxy}
- Host: {CLOUDSQL_PRIVATE_IP}

💡 Tip: Store credentials as environment variables or use Secret Manager
```
