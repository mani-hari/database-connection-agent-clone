# GCE VM → Cloud SQL Connection Guide

This file contains the complete instructions for connecting a GCE VM to Cloud SQL.
**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Variables available from previous steps:**
- `PROJECT_ID` - GCP project ID
- `USER_EMAIL` - Authenticated user email
- `CLOUDSQL_INSTANCE_NAME` - Selected Cloud SQL instance
- `CLOUDSQL_REGION` - Cloud SQL region
- `CLOUDSQL_DATABASE_VERSION` - Database type (POSTGRES_XX, MYSQL_X_X, SQLSERVER_XXXX)

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
Present VMs as numbered list. Accept number or name input.

Capture and store:
- `VM_NAME`
- `VM_ZONE`

Display confirmation:
```
✅ Selected VM: [VM_NAME] in zone [VM_ZONE]
```

**→ Ask: "Ready to proceed to Step 3 (Network Validation)? (yes/no)"**

---

## Step 3A: GCE VM Network Validation

### 3A.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,settings.ipConfiguration.authorizedNetworks,region)"
```

Extract and store:
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork)
- `CLOUDSQL_CONNECTION_NAME` (format: project:region:instance)

### 3A.2 Gather GCE VM Details
```bash
gcloud compute instances describe VM_NAME --zone=VM_ZONE --format="yaml(name,networkInterfaces[].network,networkInterfaces[].networkIP,networkInterfaces[].accessConfigs[].natIP,networkInterfaces[].subnetwork)"
```

Extract and store:
- `VM_INTERNAL_IP` (from networkInterfaces[0].networkIP)
- `VM_EXTERNAL_IP` (from networkInterfaces[0].accessConfigs[0].natIP, may be null)
- `VM_VPC` (from networkInterfaces[0].network)
- `VM_SUBNET` (from networkInterfaces[0].subnetwork)

### 3A.3 Network Analysis Output
Display results in this exact format:

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

### 3A.4 Connectivity Decision Tree

**If Private IP available AND same VPC:**
- Recommend: Direct connection via Private IP
- No additional setup required

**If Private IP available BUT different VPC:**
- Recommend: VPC Peering or move VM to Cloud SQL VPC
- Offer remediation (see 3A.5)

**If only Public IP available:**
- Warn: Less secure, recommend enabling Private IP
- Options: Cloud SQL Auth Proxy or Authorized Networks

**If no connectivity path exists:**
- Offer to enable Private IP on Cloud SQL

### 3A.5 Remediation Commands (Execute only with user consent)

**Enable Private IP on Cloud SQL:**
```bash
gcloud sql instances patch CLOUDSQL_INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/VPC_NAME \
  --no-assign-ip
```

**Check Private Services Access:**
```bash
gcloud services vpc-peerings list --network=VPC_NAME --project=PROJECT_ID
```

**Create Private Services Access (if missing):**
```bash
# Step 1: Allocate IP range
gcloud compute addresses create google-managed-services-VPC_NAME \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=VPC_NAME \
  --project=PROJECT_ID

# Step 2: Create peering connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-VPC_NAME \
  --network=VPC_NAME \
  --project=PROJECT_ID
```

**Check Firewall Rules (egress to Cloud SQL ports):**
```bash
gcloud compute firewall-rules list --filter="network:VPC_NAME AND direction=EGRESS" --format="table(name,direction,allowed,targetTags)"
```

After remediation, re-run validation checks.

**→ Ask: "Ready to proceed to Step 4 (Connection Testing)? (yes/no)"**

---

## Step 4A: GCE VM Connection Testing and Code

### 4A.1 Confirm Connection Details
Display:
```
CONNECTION SUMMARY
─────────────────────────────────
Method: [Private IP / Public IP]
Host: [IP_ADDRESS]
Port: [3306/5432/1433 based on database type]
Connection Name: [CLOUDSQL_CONNECTION_NAME]
─────────────────────────────────
```

### 4A.2 Quick Connectivity Test
Offer to test connectivity from the VM:

**For PostgreSQL:**
```bash
gcloud compute ssh VM_NAME --zone=VM_ZONE --command="pg_isready -h CLOUDSQL_PRIVATE_IP -p 5432"
```

**For MySQL:**
```bash
gcloud compute ssh VM_NAME --zone=VM_ZONE --command="mysqladmin ping -h CLOUDSQL_PRIVATE_IP --silent"
```

**For SQL Server:**
```bash
gcloud compute ssh VM_NAME --zone=VM_ZONE --command="nc -zv CLOUDSQL_PRIVATE_IP 1433"
```

### 4A.3 Language Selection
```
Select your programming language:
1. Python
2. Node.js
3. Java
4. Go
5. PHP
6. Ruby

Enter choice (1-6):
```

### 4A.4 Code Snippets

**Python (Private IP - PostgreSQL):**
```python
import sqlalchemy

def connect_with_private_ip():
    db_user = "your-db-user"
    db_pass = "your-db-password"
    db_name = "your-database"
    db_host = "CLOUDSQL_PRIVATE_IP"
    db_port = 5432

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
engine = connect_with_private_ip()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Python (Private IP - MySQL):**
```python
import sqlalchemy

def connect_with_private_ip():
    db_user = "your-db-user"
    db_pass = "your-db-password"
    db_name = "your-database"
    db_host = "CLOUDSQL_PRIVATE_IP"
    db_port = 3306

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
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
```

**Node.js (Private IP - PostgreSQL):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: 'your-db-user',
  password: 'your-db-password',
  database: 'your-database',
  host: 'CLOUDSQL_PRIVATE_IP',
  port: 5432,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query };
```

**Node.js (Private IP - MySQL):**
```javascript
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: 'CLOUDSQL_PRIVATE_IP',
  port: 3306,
  user: 'your-db-user',
  password: 'your-db-password',
  database: 'your-database',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = { pool };
```

**Java (Private IP - JDBC PostgreSQL):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    private static final String DB_URL = "jdbc:postgresql://CLOUDSQL_PRIVATE_IP:5432/your-database";
    private static final String USER = "your-db-user";
    private static final String PASS = "your-db-password";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Java (Private IP - JDBC MySQL):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    private static final String DB_URL = "jdbc:mysql://CLOUDSQL_PRIVATE_IP:3306/your-database";
    private static final String USER = "your-db-user";
    private static final String PASS = "your-db-password";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Go (Private IP - PostgreSQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/lib/pq"
)

func connectWithPrivateIP() (*sql.DB, error) {
    dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
        "CLOUDSQL_PRIVATE_IP", 5432, "your-db-user", "your-db-password", "your-database")

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Go (Private IP - MySQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/go-sql-driver/mysql"
)

func connectWithPrivateIP() (*sql.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
        "your-db-user", "your-db-password", "CLOUDSQL_PRIVATE_IP", 3306, "your-database")

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

### 4A.5 Next Steps
Recommend:
- Store credentials in Secret Manager
- Use IAM database authentication where possible
- Implement connection pooling for production
- Set up monitoring and alerting

---

## Completion

Display:
```
✅ GCE VM → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: [CLOUDSQL_INSTANCE_NAME]
- GCE VM: [VM_NAME]
- Connection Method: [Private IP / Public IP]
- Host: [IP_ADDRESS]

Next steps:
1. Store credentials securely (Secret Manager recommended)
2. Test connection from your application
3. Set up monitoring and alerting
```
