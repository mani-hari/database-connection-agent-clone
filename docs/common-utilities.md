# Cloud SQL Easy Connect - Common Utilities

Shared utilities, helpers, and reference information used across all connection methods.

---

## API Reference

### Cloud SQL Admin API

Base URL: `https://sqladmin.googleapis.com/v1`

**List Instances:**
```bash
gcloud sql instances list --format="json"
# API: GET /projects/{project}/instances
```

**Describe Instance:**
```bash
gcloud sql instances describe INSTANCE_NAME --format="json"
# API: GET /projects/{project}/instances/{instance}
```

**Get Connection Info:**
```bash
gcloud sql instances describe INSTANCE_NAME \
    --format="value(connectionName,ipAddresses)"
```

### Compute Engine API

**List VMs:**
```bash
gcloud compute instances list --format="json"
# API: GET /projects/{project}/zones/{zone}/instances
```

**Describe VM:**
```bash
gcloud compute instances describe VM_NAME --zone=ZONE --format="json"
# API: GET /projects/{project}/zones/{zone}/instances/{instance}
```

**Get VM Network:**
```bash
gcloud compute instances describe VM_NAME --zone=ZONE \
    --format="value(networkInterfaces[0].network)"
```

---

## Network Validation Functions

### Check VPC Match

```bash
#!/bin/bash
# validate_vpc_match.sh

check_vpc_match() {
    local sql_instance=$1
    local vm_name=$2
    local vm_zone=$3

    # Get Cloud SQL VPC
    SQL_VPC=$(gcloud sql instances describe ${sql_instance} \
        --format="value(settings.ipConfiguration.privateNetwork)" | awk -F'/' '{print $NF}')

    # Get VM VPC
    VM_VPC=$(gcloud compute instances describe ${vm_name} --zone=${vm_zone} \
        --format="value(networkInterfaces[0].network)" | awk -F'/' '{print $NF}')

    if [ "$SQL_VPC" == "$VM_VPC" ]; then
        echo "✅ VPC Match: Both on ${SQL_VPC}"
        return 0
    else
        echo "❌ VPC Mismatch: SQL on ${SQL_VPC}, VM on ${VM_VPC}"
        return 1
    fi
}
```

### Check Private Service Access

```bash
#!/bin/bash
# check_psa.sh

check_private_service_access() {
    local vpc_name=$1
    local project=$(gcloud config get-value project)

    echo "Checking Private Service Access for VPC: ${vpc_name}"

    # Check for service networking peering
    PEERING=$(gcloud services vpc-peerings list \
        --network=${vpc_name} \
        --project=${project} \
        --format="value(peering)" 2>/dev/null)

    if [ -n "$PEERING" ]; then
        echo "✅ Private Service Access configured: ${PEERING}"
        return 0
    else
        echo "❌ Private Service Access not configured"
        return 1
    fi
}
```

### Check Firewall Rules

```bash
#!/bin/bash
# check_firewall.sh

check_firewall_egress() {
    local vpc_name=$1
    local port=$2
    local project=$(gcloud config get-value project)

    echo "Checking firewall rules for egress on port ${port}"

    # Check for explicit deny rules
    DENY_RULES=$(gcloud compute firewall-rules list \
        --filter="network:${vpc_name} AND direction=EGRESS AND denied.ports=${port}" \
        --format="value(name)" 2>/dev/null)

    if [ -n "$DENY_RULES" ]; then
        echo "❌ Found deny rules: ${DENY_RULES}"
        return 1
    fi

    # Check for allow rules (default allows all egress)
    echo "✅ No blocking firewall rules found"
    return 0
}
```

---

## Database Port Reference

| Database | Default Port | SSL Port |
|----------|-------------|----------|
| PostgreSQL | 5432 | 5432 |
| MySQL | 3306 | 3306 |
| SQL Server | 1433 | 1433 |

---

## Connection String Templates

### PostgreSQL

**Standard:**
```
postgresql://${USER}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}?sslmode=require
```

**With SSL certificates:**
```
postgresql://${USER}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}?sslmode=verify-full&sslrootcert=server-ca.pem&sslcert=client-cert.pem&sslkey=client-key.pem
```

### MySQL

**Standard:**
```
mysql://${USER}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}?ssl-mode=REQUIRED
```

**With SSL:**
```
mysql://${USER}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}?ssl-ca=server-ca.pem&ssl-cert=client-cert.pem&ssl-key=client-key.pem
```

### SQL Server

**Standard:**
```
Server=${HOST},${PORT};Database=${DATABASE};User Id=${USER};Password=${PASSWORD};Encrypt=True;
```

---

## IAM Roles Reference

### Minimum Required Roles

| Role | Description | When Needed |
|------|-------------|-------------|
| `roles/cloudsql.client` | Connect to Cloud SQL | Always |
| `roles/cloudsql.instanceUser` | IAM database auth | For IAM auth |
| `roles/compute.viewer` | View VM details | GCE connections |
| `roles/compute.osLogin` | SSH to VMs | Connection testing |

### Grant Role Command

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="user:USER_EMAIL" \
    --role="ROLE_NAME"
```

---

## Error Codes & Solutions

### Connection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Wrong host/port or service down | Verify host, port, and Cloud SQL is running |
| `Connection timed out` | Network/firewall blocking | Check VPC, firewall rules, authorized networks |
| `Permission denied` | IAM or database permissions | Grant `roles/cloudsql.client` and database user permissions |
| `SSL required` | SSL not configured | Add SSL parameters to connection string |

### Auth Proxy Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Error creating dialer` | Auth failure | Run `gcloud auth application-default login` |
| `Connection refused on 127.0.0.1:XXXX` | Proxy not running | Start the Auth Proxy |
| `Instance not found` | Wrong connection name | Verify `project:region:instance` format |

---

## Diagnostic Commands

### Full Diagnostic Script

```bash
#!/bin/bash
# diagnose_connection.sh

diagnose_cloudsql_connection() {
    local instance=$1
    local project=$(gcloud config get-value project)

    echo "=========================================="
    echo "Cloud SQL Connection Diagnostic"
    echo "=========================================="

    echo -e "\n1. Authentication Check:"
    gcloud auth list --filter="status:ACTIVE" --format="value(account)"

    echo -e "\n2. Project:"
    echo $project

    echo -e "\n3. Cloud SQL Instance Details:"
    gcloud sql instances describe $instance \
        --format="table(name,state,region,databaseVersion)"

    echo -e "\n4. IP Configuration:"
    gcloud sql instances describe $instance \
        --format="yaml(ipAddresses,settings.ipConfiguration)"

    echo -e "\n5. IAM Permissions Check:"
    USER=$(gcloud config get-value account)
    gcloud projects get-iam-policy $project \
        --filter="bindings.members:user:$USER" \
        --flatten="bindings[].members" \
        --format="table(bindings.role)"

    echo -e "\n6. API Enablement:"
    gcloud services list --enabled --filter="NAME:sqladmin.googleapis.com"

    echo "=========================================="
    echo "Diagnostic Complete"
    echo "=========================================="
}

# Usage: diagnose_cloudsql_connection my-instance
```

---

## Code Snippet: Retry Logic

### Python

```python
import time
from functools import wraps

def retry_connection(max_retries=3, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    print(f"Connection failed, retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

@retry_connection(max_retries=3, delay=2)
def connect_to_database():
    # Your connection code here
    pass
```

### Node.js

```javascript
async function retryConnection(connectFn, maxRetries = 3, delay = 2000) {
    let lastError;
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await connectFn();
        } catch (error) {
            lastError = error;
            console.log(`Connection failed, retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2; // Exponential backoff
        }
    }
    throw lastError;
}
```

---

## Environment Setup Templates

### .env Template

```bash
# Cloud SQL Configuration
CLOUD_SQL_CONNECTION_NAME=project:region:instance
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=mydatabase
DB_USER=myuser
DB_PASSWORD=

# GCP Configuration
GCP_PROJECT=my-project
GCP_REGION=us-central1
```

### Docker Compose with Auth Proxy

```yaml
version: '3.8'
services:
  cloud-sql-proxy:
    image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.19.0
    command:
      - "--port=5432"
      - "${CLOUD_SQL_CONNECTION_NAME}"
    ports:
      - "5432:5432"
    volumes:
      - ~/.config/gcloud:/root/.config/gcloud:ro

  app:
    build: .
    depends_on:
      - cloud-sql-proxy
    environment:
      - DB_HOST=cloud-sql-proxy
      - DB_PORT=5432
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│              CLOUD SQL QUICK REFERENCE                      │
├─────────────────────────────────────────────────────────────┤
│ List instances:     gcloud sql instances list               │
│ Describe instance:  gcloud sql instances describe NAME      │
│ Get connection:     gcloud sql instances describe NAME \    │
│                     --format="value(connectionName)"        │
├─────────────────────────────────────────────────────────────┤
│ Start Auth Proxy:   cloud-sql-proxy --port PORT CONN_NAME   │
│ Test PostgreSQL:    psql -h 127.0.0.1 -U USER -d DB         │
│ Test MySQL:         mysql -h 127.0.0.1 -u USER -p DB        │
├─────────────────────────────────────────────────────────────┤
│ Ports: PostgreSQL=5432, MySQL=3306, SQL Server=1433         │
│ Connection Name Format: project:region:instance             │
└─────────────────────────────────────────────────────────────┘
```
