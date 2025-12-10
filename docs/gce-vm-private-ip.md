# Cloud SQL Connection: GCE VM via Private IP

This instruction set guides connecting a Google Compute Engine VM to Cloud SQL using Private IP connectivity.

---

## Prerequisites Check

Before starting, verify:

```bash
# Verify you're authenticated
gcloud auth list

# Verify current project
gcloud config get-value project

# Ensure you have necessary permissions
# Required roles: roles/cloudsql.client, roles/compute.viewer
```

---

## STEP 1: Gather Information

### 1.1 Get Cloud SQL Instance Details

```bash
# List Cloud SQL instances
gcloud sql instances list --format="table(name,databaseVersion,region,settings.ipConfiguration.privateNetwork)"

# User prompt: "Which Cloud SQL instance do you want to connect to?"
# Store as: CLOUD_SQL_INSTANCE

# Get instance details
gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="json(name,connectionName,ipAddresses,region,settings.ipConfiguration)"
```

**Extract and store:**
- `CONNECTION_NAME`: project:region:instance format
- `PRIVATE_IP`: The private IP address
- `VPC_NETWORK`: The VPC network name from privateNetwork field
- `REGION`: Instance region
- `DB_VERSION`: postgresql, mysql, or sqlserver

### 1.2 Get GCE VM Details

```bash
# List all VMs in the project
gcloud compute instances list --format="table(name,zone,networkInterfaces[0].network,networkInterfaces[0].networkIP,status)"

# User prompt: "Which GCE VM do you want to connect from?"
# Store as: VM_NAME, VM_ZONE

# Get VM details
gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="json(name,networkInterfaces,zone)"
```

**Extract and store:**
- `VM_NETWORK`: The VPC network the VM is connected to
- `VM_INTERNAL_IP`: The VM's internal IP
- `VM_ZONE`: The VM's zone

---

## STEP 2: Network Validation

### 2.1 Check VPC Network Match

```bash
# Extract network names for comparison
CLOUD_SQL_VPC=$(gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="value(settings.ipConfiguration.privateNetwork)" | awk -F'/' '{print $NF}')

VM_VPC=$(gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="value(networkInterfaces[0].network)" | awk -F'/' '{print $NF}')

echo "Cloud SQL VPC: ${CLOUD_SQL_VPC}"
echo "VM VPC: ${VM_VPC}"
```

### 2.2 Validation Decision Tree

```
IF CLOUD_SQL_VPC == VM_VPC:
    ✅ PASS - Same VPC network
    → Proceed to Step 3

ELSE IF VPC Peering exists between networks:
    ✅ PASS - Networks are peered
    → Proceed to Step 3

ELSE:
    ❌ FAIL - Network mismatch
    → Go to Remediation Section
```

### 2.3 Check Private Service Access

```bash
# Verify Private Service Access is configured
gcloud services vpc-peerings list --network=${VM_VPC} --project=$(gcloud config get-value project)

# Look for servicenetworking.googleapis.com peering
```

### 2.4 Check Firewall Rules

```bash
# List firewall rules that might affect connectivity
gcloud compute firewall-rules list --filter="network:${VM_VPC}" --format="table(name,direction,allowed,targetTags)"

# Verify egress is allowed to Cloud SQL port
# PostgreSQL: 5432, MySQL: 3306, SQL Server: 1433
```

---

## STEP 2B: Remediation (If Network Validation Fails)

### If Cloud SQL doesn't have Private IP enabled:

**Option A: Enable Private IP on Cloud SQL (Recommended)**
```bash
# Note: This may cause brief downtime
gcloud sql instances patch ${CLOUD_SQL_INSTANCE} \
    --network=projects/$(gcloud config get-value project)/global/networks/${VM_VPC} \
    --no-assign-ip  # Optional: disable public IP for security
```

**Trade-offs:**
- ✅ More secure (no public exposure)
- ✅ Better network performance
- ⚠️ May require Private Service Access setup
- ⚠️ Brief connectivity interruption during change

### If VM is on different network:

**Option A: Move VM to Cloud SQL's VPC**
```bash
# Create new VM in correct VPC (cannot change existing VM's network)
# This requires recreating the VM
```

**Option B: Set up VPC Peering**
```bash
gcloud compute networks peerings create peer-to-cloudsql-vpc \
    --network=${VM_VPC} \
    --peer-network=${CLOUD_SQL_VPC}
```

**Trade-offs:**
- Option A: Clean solution but requires VM recreation
- Option B: Keeps existing VM but adds network complexity

### If Private Service Access not configured:

```bash
# Allocate IP range for private services
gcloud compute addresses create google-managed-services-${VM_VPC} \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network=${VM_VPC}

# Create private connection
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=google-managed-services-${VM_VPC} \
    --network=${VM_VPC}
```

---

## STEP 3: Connection Test

### 3.1 SSH into the GCE VM

```bash
gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE}
```

### 3.2 Install Database Client

**For PostgreSQL:**
```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y postgresql-client

# Verify installation
psql --version
```

**For MySQL:**
```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y mysql-client

# Verify installation
mysql --version
```

**For SQL Server:**
```bash
# Add Microsoft repository and install sqlcmd
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/msprod.list
sudo apt-get update && sudo apt-get install -y mssql-tools unixodbc-dev
```

### 3.3 Get Database Credentials

```bash
# User prompt: "What is your database username?"
# Store as: DB_USER

# User prompt: "What is your database password?"
# Store as: DB_PASSWORD (handle securely)

# User prompt: "What is your database name?"
# Store as: DB_NAME
```

### 3.4 Test Connection

**For PostgreSQL:**
```bash
psql "host=${PRIVATE_IP} port=5432 dbname=${DB_NAME} user=${DB_USER} password=${DB_PASSWORD} sslmode=require"

# Quick test query
# \conninfo
# SELECT version();
# \q
```

**For MySQL:**
```bash
mysql -h ${PRIVATE_IP} -u ${DB_USER} -p${DB_PASSWORD} ${DB_NAME} --ssl-mode=REQUIRED

# Quick test query
# SELECT VERSION();
# exit
```

**For SQL Server:**
```bash
sqlcmd -S ${PRIVATE_IP} -U ${DB_USER} -P ${DB_PASSWORD} -d ${DB_NAME}

# Quick test query
# SELECT @@VERSION;
# GO
# exit
```

### 3.5 Validate Connection Success

```
IF connection successful:
    ✅ "Connection test PASSED!"
    → Proceed to Step 4

ELSE:
    ❌ "Connection test FAILED"
    → Check error message
    → Verify credentials
    → Check firewall rules
    → Verify SSL configuration
```

---

## STEP 4: Generate Application Code

### 4.1 Ask Programming Language

```
What programming language is your application written in?
1. Python
2. Node.js
3. Java
4. Go
5. PHP
6. Ruby
7. .NET / C#
```

### 4.2 Connection Strings and Code Samples

#### Python (PostgreSQL)

**Install dependencies:**
```bash
pip install pg8000 sqlalchemy cloud-sql-python-connector
```

**Connection code:**
```python
import sqlalchemy
from google.cloud.sql.connector import Connector

# Initialize connector
connector = Connector()

def getconn():
    conn = connector.connect(
        "${CONNECTION_NAME}",  # e.g., project:region:instance
        "pg8000",
        user="${DB_USER}",
        password="${DB_PASSWORD}",
        db="${DB_NAME}",
        ip_type="PRIVATE"  # Use private IP
    )
    return conn

# Create SQLAlchemy engine
engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

# Use the engine
with engine.connect() as connection:
    result = connection.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())

# Clean up
connector.close()
```

**Or simple connection string (without connector):**
```python
import psycopg2

conn = psycopg2.connect(
    host="${PRIVATE_IP}",
    port=5432,
    database="${DB_NAME}",
    user="${DB_USER}",
    password="${DB_PASSWORD}",
    sslmode="require"
)
```

#### Python (MySQL)

**Install dependencies:**
```bash
pip install pymysql sqlalchemy cloud-sql-python-connector
```

**Connection code:**
```python
import sqlalchemy
from google.cloud.sql.connector import Connector

connector = Connector()

def getconn():
    conn = connector.connect(
        "${CONNECTION_NAME}",
        "pymysql",
        user="${DB_USER}",
        password="${DB_PASSWORD}",
        db="${DB_NAME}",
        ip_type="PRIVATE"
    )
    return conn

engine = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)
```

#### Node.js (PostgreSQL)

**Install dependencies:**
```bash
npm install pg @google-cloud/cloud-sql-connector
```

**Connection code:**
```javascript
const { Connector } = require('@google-cloud/cloud-sql-connector');
const { Pool } = require('pg');

const connector = new Connector();

async function connect() {
    const clientOpts = await connector.getOptions({
        instanceConnectionName: '${CONNECTION_NAME}',
        ipType: 'PRIVATE',
    });

    const pool = new Pool({
        ...clientOpts,
        user: '${DB_USER}',
        password: '${DB_PASSWORD}',
        database: '${DB_NAME}',
    });

    const result = await pool.query('SELECT NOW()');
    console.log(result.rows);

    await pool.end();
    connector.close();
}

connect();
```

#### Java (PostgreSQL)

**Maven dependency:**
```xml
<dependency>
    <groupId>com.google.cloud.sql</groupId>
    <artifactId>postgres-socket-factory</artifactId>
    <version>1.15.0</version>
</dependency>
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.6.0</version>
</dependency>
```

**Connection code:**
```java
import java.sql.Connection;
import java.sql.DriverManager;

String jdbcUrl = String.format(
    "jdbc:postgresql:///${DB_NAME}?" +
    "cloudSqlInstance=${CONNECTION_NAME}&" +
    "socketFactory=com.google.cloud.sql.postgres.SocketFactory&" +
    "ipTypes=PRIVATE&" +
    "user=${DB_USER}&" +
    "password=${DB_PASSWORD}"
);

Connection conn = DriverManager.getConnection(jdbcUrl);
```

#### Go (PostgreSQL)

**Install dependencies:**
```bash
go get cloud.google.com/go/cloudsqlconn
go get github.com/jackc/pgx/v5
```

**Connection code:**
```go
package main

import (
    "context"
    "database/sql"
    "fmt"
    "net"

    "cloud.google.com/go/cloudsqlconn"
    "github.com/jackc/pgx/v5"
    "github.com/jackc/pgx/v5/stdlib"
)

func connect() (*sql.DB, error) {
    d, err := cloudsqlconn.NewDialer(context.Background(),
        cloudsqlconn.WithDefaultDialOptions(cloudsqlconn.WithPrivateIP()))
    if err != nil {
        return nil, err
    }

    config, err := pgx.ParseConfig(
        "user=${DB_USER} password=${DB_PASSWORD} dbname=${DB_NAME}")
    if err != nil {
        return nil, err
    }

    config.DialFunc = func(ctx context.Context, network, addr string) (net.Conn, error) {
        return d.Dial(ctx, "${CONNECTION_NAME}")
    }

    dbURI := stdlib.RegisterConnConfig(config)
    return sql.Open("pgx", dbURI)
}
```

---

## STEP 5: Best Practices Reminder

✅ **Security:**
- Store credentials in Secret Manager, not in code
- Use IAM database authentication when possible
- Enable SSL/TLS (enforced by default in Cloud SQL)
- Use Private IP (you've already done this!)

✅ **Performance:**
- Use connection pooling
- Keep connections in the same region
- Monitor with Cloud SQL Insights

✅ **Reliability:**
- Implement connection retry logic
- Use Cloud SQL high availability
- Set up automated backups

---

## Success!

🎉 Your GCE VM is now connected to Cloud SQL via Private IP!

**Summary:**
- Cloud SQL Instance: `${CLOUD_SQL_INSTANCE}`
- Connection Name: `${CONNECTION_NAME}`
- Private IP: `${PRIVATE_IP}`
- GCE VM: `${VM_NAME}`
- Connection Method: Private IP (Secure)
