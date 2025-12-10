# Cloud Run → Cloud SQL Connection Guide

This file contains the complete instructions for connecting a Cloud Run service to Cloud SQL.
**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Variables available from previous steps:**
- `PROJECT_ID` - GCP project ID
- `USER_EMAIL` - Authenticated user email
- `CLOUDSQL_INSTANCE_NAME` - Selected Cloud SQL instance
- `CLOUDSQL_REGION` - Cloud SQL region
- `CLOUDSQL_DATABASE_VERSION` - Database type (POSTGRES_XX, MYSQL_X_X, SQLSERVER_XXXX)

---

## Step 2D: Cloud Run Service Selection

### 2D.1 Check for Existing Services
```
Fetching Cloud Run services... please wait
```

```bash
gcloud run services list --format="table(name,region,status)" --platform=managed
```

### 2D.2 User Selection
Ask user:
```
Do you want to:
1. Connect an existing Cloud Run service to Cloud SQL
2. Set up connection for a new Cloud Run service (not yet deployed)

Enter choice (1-2):
```

**If Option 1 (Existing Service):**
Present services as numbered list. Accept number or name input.

Capture and store:
- `CLOUDRUN_SERVICE_NAME`
- `CLOUDRUN_REGION`

**If Option 2 (New Service):**
Ask for planned service name and region:
```
Enter the name for your new Cloud Run service:
Enter the region (e.g., us-central1):
```

Store:
- `CLOUDRUN_SERVICE_NAME`
- `CLOUDRUN_REGION`

Display confirmation:
```
✅ Service: [CLOUDRUN_SERVICE_NAME] in [CLOUDRUN_REGION]
```

**→ Ask: "Ready to proceed to Step 3 (Connection Configuration)? (yes/no)"**

---

## Step 3D: Cloud Run Connection Configuration

### 3D.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,region)"
```

Extract and store:
- `CLOUDSQL_CONNECTION_NAME` (format: project:region:instance)
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)

### 3D.2 Check Existing Service Configuration (if existing service)
```bash
gcloud run services describe CLOUDRUN_SERVICE_NAME --region=CLOUDRUN_REGION --format="yaml(spec.template.metadata.annotations,spec.template.spec.serviceAccountName)"
```

### 3D.3 Connection Method Selection
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

Select connection method (1-3):
```

### 3D.4 Service Account Setup

**Check or create service account:**
```bash
gcloud iam service-accounts list --filter="email:cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com" --format="value(email)"
```

**If not exists, create:**
```bash
gcloud iam service-accounts create cloudrun-sql-sa \
  --display-name="Cloud Run Cloud SQL Service Account"
```

**Grant Cloud SQL Client role:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### 3D.5 Connection Method Configuration

#### Option 1: Built-in Cloud SQL Connection (Recommended)

This method uses Cloud Run's native Cloud SQL integration via Unix socket.

**For existing service - add Cloud SQL connection:**
```bash
gcloud run services update CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --add-cloudsql-instances=CLOUDSQL_CONNECTION_NAME \
  --service-account=cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com
```

**For new deployment:**
```bash
gcloud run deploy CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --image=YOUR_IMAGE \
  --add-cloudsql-instances=CLOUDSQL_CONNECTION_NAME \
  --service-account=cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="INSTANCE_CONNECTION_NAME=CLOUDSQL_CONNECTION_NAME,DB_NAME=your-database,DB_USER=your-user"
```

**Connection path in application:**
- PostgreSQL: `/cloudsql/CLOUDSQL_CONNECTION_NAME/.s.PGSQL.5432`
- MySQL: `/cloudsql/CLOUDSQL_CONNECTION_NAME`
- SQL Server: Not supported via Unix socket (use Option 2 or 3)

#### Option 2: Private IP via VPC Connector

**Step 1: Create VPC Connector (if not exists):**
```bash
gcloud compute networks vpc-access connectors create cloudrun-connector \
  --region=CLOUDRUN_REGION \
  --network=VPC_NAME \
  --range=10.8.0.0/28
```

**Step 2: Deploy/Update with VPC Connector:**
```bash
gcloud run services update CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --vpc-connector=cloudrun-connector \
  --vpc-egress=private-ranges-only \
  --service-account=cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="DB_HOST=CLOUDSQL_PRIVATE_IP,DB_PORT=5432,DB_NAME=your-database,DB_USER=your-user"
```

#### Option 3: Direct VPC Egress

**Deploy/Update with Direct VPC Egress:**
```bash
gcloud run services update CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --network=VPC_NAME \
  --subnet=SUBNET_NAME \
  --vpc-egress=all-traffic \
  --service-account=cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="DB_HOST=CLOUDSQL_PRIVATE_IP,DB_PORT=5432,DB_NAME=your-database,DB_USER=your-user"
```

### 3D.6 Set Database Credentials

**Using environment variables (for development):**
```bash
gcloud run services update CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --set-env-vars="DB_USER=your-user,DB_PASS=your-password,DB_NAME=your-database"
```

**Using Secret Manager (recommended for production):**

Create secrets:
```bash
echo -n "your-db-user" | gcloud secrets create db-user --data-file=-
echo -n "your-db-password" | gcloud secrets create db-password --data-file=-
echo -n "your-database" | gcloud secrets create db-name --data-file=-
```

Grant access to service account:
```bash
gcloud secrets add-iam-policy-binding db-user \
  --member="serviceAccount:cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding db-name \
  --member="serviceAccount:cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Deploy with secrets:
```bash
gcloud run services update CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --set-secrets="DB_USER=db-user:latest,DB_PASS=db-password:latest,DB_NAME=db-name:latest"
```

**→ Ask: "Ready to proceed to Step 4 (Code Configuration)? (yes/no)"**

---

## Step 4D: Cloud Run Application Code

### 4D.1 Connection Summary
```
CONNECTION SUMMARY
─────────────────────────────────
Cloud Run Service: [CLOUDRUN_SERVICE_NAME]
Cloud SQL Instance: [CLOUDSQL_CONNECTION_NAME]
Connection Method: [Built-in / VPC Connector / Direct VPC]
─────────────────────────────────
```

### 4D.2 Language Selection
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

### 4D.3 Code Snippets

#### Option 1: Built-in Cloud SQL Connection (Unix Socket)

**Python (Unix Socket - PostgreSQL):**
```python
import os
import sqlalchemy

def connect_unix_socket():
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

    unix_socket_path = f"/cloudsql/{instance_connection_name}"

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"unix_sock": f"{unix_socket_path}/.s.PGSQL.5432"},
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_unix_socket()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Python (Unix Socket - MySQL):**
```python
import os
import sqlalchemy

def connect_unix_socket():
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]

    unix_socket_path = f"/cloudsql/{instance_connection_name}"

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"unix_socket": unix_socket_path},
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool
```

**Python (Cloud SQL Connector - Recommended):**
```python
# pip install cloud-sql-python-connector[pg8000]
import os
from google.cloud.sql.connector import Connector
import sqlalchemy

def connect_with_connector():
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]

    connector = Connector()

    def getconn():
        conn = connector.connect(
            instance_connection_name,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool
```

**Node.js (Unix Socket - PostgreSQL):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  host: `/cloudsql/${process.env.INSTANCE_CONNECTION_NAME}`,
  max: 10,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query, pool };
```

**Node.js (Cloud SQL Connector):**
```javascript
const { Connector } = require('@google-cloud/cloud-sql-connector');

async function connect() {
  const connector = new Connector();
  const clientOpts = await connector.getOptions({
    instanceConnectionName: process.env.INSTANCE_CONNECTION_NAME,
  });

  const { Pool } = require('pg');
  const pool = new Pool({
    ...clientOpts,
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    database: process.env.DB_NAME,
    max: 10,
  });

  return pool;
}

module.exports = { connect };
```

**Go (Unix Socket - PostgreSQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    "os"

    _ "github.com/jackc/pgx/v4/stdlib"
)

func connectUnixSocket() (*sql.DB, error) {
    var (
        dbUser                 = os.Getenv("DB_USER")
        dbPwd                  = os.Getenv("DB_PASS")
        dbName                 = os.Getenv("DB_NAME")
        instanceConnectionName = os.Getenv("INSTANCE_CONNECTION_NAME")
        socketDir              = "/cloudsql"
    )

    dsn := fmt.Sprintf("user=%s password=%s database=%s host=%s/%s",
        dbUser, dbPwd, dbName, socketDir, instanceConnectionName)

    db, err := sql.Open("pgx", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Java (Unix Socket - JDBC PostgreSQL):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudRunConnection {
    public static Connection getConnection() throws SQLException {
        String dbUser = System.getenv("DB_USER");
        String dbPass = System.getenv("DB_PASS");
        String dbName = System.getenv("DB_NAME");
        String instanceConnectionName = System.getenv("INSTANCE_CONNECTION_NAME");

        String socketPath = "/cloudsql/" + instanceConnectionName;
        String jdbcUrl = String.format(
            "jdbc:postgresql:///%s?cloudSqlInstance=%s&socketFactory=com.google.cloud.sql.postgres.SocketFactory",
            dbName, instanceConnectionName
        );

        return DriverManager.getConnection(jdbcUrl, dbUser, dbPass);
    }
}
```

#### Option 2 & 3: Private IP Connection

**Python (Private IP):**
```python
import os
import sqlalchemy

def connect_tcp():
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]
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
```

**Node.js (Private IP):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT) || 5432,
  max: 10,
});

module.exports = { pool };
```

### 4D.4 Dockerfile Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets PORT environment variable
ENV PORT=8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
```

**requirements.txt:**
```
Flask==3.0.0
gunicorn==21.2.0
SQLAlchemy==2.0.23
pg8000==1.30.3
cloud-sql-python-connector[pg8000]==1.6.0
```

### 4D.5 Verify Deployment

**Check service status:**
```bash
gcloud run services describe CLOUDRUN_SERVICE_NAME --region=CLOUDRUN_REGION --format="yaml(status)"
```

**View logs:**
```bash
gcloud run services logs read CLOUDRUN_SERVICE_NAME --region=CLOUDRUN_REGION --limit=50
```

**Test the service:**
```bash
curl $(gcloud run services describe CLOUDRUN_SERVICE_NAME --region=CLOUDRUN_REGION --format="value(status.url)")
```

### 4D.6 Production Recommendations

```
PRODUCTION RECOMMENDATIONS
─────────────────────────────────
1. Use Secret Manager for credentials (not env vars)

2. Connection Pooling:
   - Cloud Run scales to zero - connections close
   - Use Cloud SQL Connector for automatic reconnection
   - Set appropriate pool_recycle (1800 seconds)

3. Cold Start Optimization:
   - Keep min-instances=1 if latency matters
   - Use connection pooling libraries

4. Monitoring:
   - Enable Cloud SQL insights
   - Set up alerts for connection errors
   - Monitor Cloud Run metrics

5. Security:
   - Use dedicated service account
   - Enable VPC if additional security needed
   - Use IAM database authentication
─────────────────────────────────
```

---

## Completion

Display:
```
✅ Cloud Run → Cloud SQL connection setup complete!

Summary:
- Cloud Run Service: [CLOUDRUN_SERVICE_NAME]
- Cloud SQL Instance: [CLOUDSQL_CONNECTION_NAME]
- Connection Method: [Built-in / VPC Connector / Direct VPC]
- Service Account: cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com

Deploy command:
gcloud run deploy CLOUDRUN_SERVICE_NAME \
  --region=CLOUDRUN_REGION \
  --image=YOUR_IMAGE \
  --add-cloudsql-instances=CLOUDSQL_CONNECTION_NAME \
  --service-account=cloudrun-sql-sa@PROJECT_ID.iam.gserviceaccount.com

Next steps:
1. Build and push your container image
2. Deploy with the command above
3. Verify connection in Cloud Run logs
```
