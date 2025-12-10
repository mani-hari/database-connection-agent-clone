# Local IDE / Laptop → Cloud SQL Connection Guide

This file contains the complete instructions for connecting from a local development environment to Cloud SQL.
**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Variables available from previous steps:**
- `PROJECT_ID` - GCP project ID
- `USER_EMAIL` - Authenticated user email
- `CLOUDSQL_INSTANCE_NAME` - Selected Cloud SQL instance
- `CLOUDSQL_REGION` - Cloud SQL region
- `CLOUDSQL_DATABASE_VERSION` - Database type (POSTGRES_XX, MYSQL_X_X, SQLSERVER_XXXX)

---

## Step 2B: Local Development Setup

### 2B.1 Verify Local gcloud Authentication
```bash
gcloud auth application-default print-access-token
```

**If token is returned:** User has Application Default Credentials. Display:
```
✅ Application Default Credentials configured
```

**If error or no token:** Run:
```bash
gcloud auth application-default login
```

### 2B.2 Confirm Cloud SQL Admin API is Enabled
```bash
gcloud services list --enabled --filter="name:sqladmin.googleapis.com" --format="value(name)"
```

**If output is empty (API not enabled):**
```bash
gcloud services enable sqladmin.googleapis.com
```

Display confirmation:
```
✅ Cloud SQL Admin API: Enabled
✅ Application Default Credentials: Configured
```

**→ Ask: "Ready to proceed to Step 3 (Auth Proxy Setup)? (yes/no)"**

---

## Step 3B: Cloud SQL Auth Proxy Setup

### 3B.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(connectionName,ipAddresses,settings.ipConfiguration)"
```

Store:
- `CLOUDSQL_CONNECTION_NAME` (format: project:region:instance)

### 3B.2 Network Analysis Output
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

### 3B.3 Check IAM Permissions
```bash
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:user:USER_EMAIL" --format="table(bindings.role)"
```

Required role: `roles/cloudsql.client` or `roles/cloudsql.editor`

**If missing, offer to grant:**
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:USER_EMAIL" \
  --role="roles/cloudsql.client"
```

### 3B.4 Install Cloud SQL Auth Proxy

Ask user for their operating system, then provide the appropriate command:

**macOS (Apple Silicon / M1/M2/M3):**
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.arm64
chmod +x cloud-sql-proxy
```

**macOS (Intel):**
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy
```

**Linux (amd64):**
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
```

**Linux (arm64):**
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.arm64
chmod +x cloud-sql-proxy
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.x64.exe" -OutFile "cloud-sql-proxy.exe"
```

### 3B.5 Start Auth Proxy

Determine the port based on database type:
- PostgreSQL: 5432
- MySQL: 3306
- SQL Server: 1433

**Start command:**
```bash
./cloud-sql-proxy CLOUDSQL_CONNECTION_NAME --port=LOCAL_PORT
```

**Example for PostgreSQL:**
```bash
./cloud-sql-proxy my-project:us-central1:my-postgres-db --port=5432
```

Display:
```
✅ Auth Proxy installed
✅ Start command ready

Run in a separate terminal:
./cloud-sql-proxy CLOUDSQL_CONNECTION_NAME --port=LOCAL_PORT

Keep this running while developing.
```

**→ Ask: "Ready to proceed to Step 4 (Connection Testing)? (yes/no)"**

---

## Step 4B: Local Connection Testing and Code

### 4B.1 Connection Summary
```
CONNECTION SUMMARY
─────────────────────────────────
Method: Cloud SQL Auth Proxy
Host: 127.0.0.1
Port: [5432/3306/1433]
Proxy Connection: [CLOUDSQL_CONNECTION_NAME]
─────────────────────────────────
```

### 4B.2 Test Connection

Offer to test connectivity (Auth Proxy must be running):

**PostgreSQL:**
```bash
psql "host=127.0.0.1 port=5432 user=YOUR_USER dbname=YOUR_DB"
```

**MySQL:**
```bash
mysql -h 127.0.0.1 -P 3306 -u YOUR_USER -p YOUR_DB
```

**SQL Server:**
```bash
sqlcmd -S 127.0.0.1,1433 -U YOUR_USER -P YOUR_PASSWORD -d YOUR_DB
```

### 4B.3 Language Selection
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

### 4B.4 Code Snippets

#### Option A: Via Auth Proxy (simpler setup)

**Python (Auth Proxy - PostgreSQL):**
```python
import sqlalchemy

def connect_via_proxy():
    db_user = "your-db-user"
    db_pass = "your-db-password"
    db_name = "your-database"

    # Auth Proxy runs on localhost
    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            host="127.0.0.1",
            port=5432,
            database=db_name,
        ),
    )
    return pool

# Usage
engine = connect_via_proxy()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Python (Auth Proxy - MySQL):**
```python
import sqlalchemy

def connect_via_proxy():
    db_user = "your-db-user"
    db_pass = "your-db-password"
    db_name = "your-database"

    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host="127.0.0.1",
            port=3306,
            database=db_name,
        ),
    )
    return pool
```

**Node.js (Auth Proxy - PostgreSQL):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: 'your-db-user',
  password: 'your-db-password',
  database: 'your-database',
  host: '127.0.0.1',
  port: 5432,
  max: 10,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query };
```

**Node.js (Auth Proxy - MySQL):**
```javascript
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: '127.0.0.1',
  port: 3306,
  user: 'your-db-user',
  password: 'your-db-password',
  database: 'your-database',
  waitForConnections: true,
  connectionLimit: 10,
});

module.exports = { pool };
```

**Go (Auth Proxy - PostgreSQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/lib/pq"
)

func connectViaProxy() (*sql.DB, error) {
    dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
        "127.0.0.1", 5432, "your-db-user", "your-db-password", "your-database")

    return sql.Open("postgres", dsn)
}
```

**Java (Auth Proxy - JDBC):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Auth Proxy runs on localhost
    private static final String DB_URL = "jdbc:postgresql://127.0.0.1:5432/your-database";
    private static final String USER = "your-db-user";
    private static final String PASS = "your-db-password";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

#### Option B: Via Cloud SQL Connector (no separate proxy needed)

**Python (Cloud SQL Connector - PostgreSQL):**
```python
# pip install cloud-sql-python-connector[pg8000]
from google.cloud.sql.connector import Connector
import sqlalchemy

def connect_with_connector():
    connector = Connector()

    def getconn():
        conn = connector.connect(
            "CLOUDSQL_CONNECTION_NAME",  # e.g., "project:region:instance"
            "pg8000",
            user="your-db-user",
            password="your-db-password",
            db="your-database",
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
    return pool

# Usage
engine = connect_with_connector()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Python (Cloud SQL Connector - MySQL):**
```python
# pip install cloud-sql-python-connector[pymysql]
from google.cloud.sql.connector import Connector
import sqlalchemy

def connect_with_connector():
    connector = Connector()

    def getconn():
        conn = connector.connect(
            "CLOUDSQL_CONNECTION_NAME",
            "pymysql",
            user="your-db-user",
            password="your-db-password",
            db="your-database",
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
    )
    return pool
```

**Node.js (Cloud SQL Connector):**
```javascript
// npm install @google-cloud/cloud-sql-connector
const { Connector } = require('@google-cloud/cloud-sql-connector');

async function connect() {
  const connector = new Connector();
  const clientOpts = await connector.getOptions({
    instanceConnectionName: 'CLOUDSQL_CONNECTION_NAME',
  });

  const { Pool } = require('pg');
  const pool = new Pool({
    ...clientOpts,
    user: 'your-db-user',
    password: 'your-db-password',
    database: 'your-database',
  });

  return pool;
}

module.exports = { connect };
```

**Go (Cloud SQL Connector):**
```go
// go get cloud.google.com/go/cloudsqlconn
package main

import (
    "context"
    "database/sql"
    "net"

    "cloud.google.com/go/cloudsqlconn"
    "github.com/jackc/pgx/v4/stdlib"
)

func connectWithConnector() (*sql.DB, error) {
    ctx := context.Background()

    d, err := cloudsqlconn.NewDialer(ctx)
    if err != nil {
        return nil, err
    }

    dsn := "user=your-db-user password=your-db-password dbname=your-database sslmode=disable"
    config, err := pgx.ParseConfig(dsn)
    if err != nil {
        return nil, err
    }

    config.DialFunc = func(ctx context.Context, network, addr string) (net.Conn, error) {
        return d.Dial(ctx, "CLOUDSQL_CONNECTION_NAME")
    }

    return stdlib.OpenDB(*config), nil
}
```

### 4B.5 Development Workflow Tips

Display these tips:
```
DEVELOPMENT TIPS
─────────────────────────────────
1. Keep Auth Proxy running in a separate terminal
2. Use environment variables for credentials:
   export DB_USER="your-user"
   export DB_PASS="your-password"

3. Use .env files (add to .gitignore!):
   DB_HOST=127.0.0.1
   DB_PORT=5432
   DB_USER=your-user
   DB_PASS=your-password
   DB_NAME=your-database

4. Consider Cloud SQL Connector libraries for:
   - No separate proxy process
   - Automatic IAM authentication
   - Built-in connection management
─────────────────────────────────
```

---

## Completion

Display:
```
✅ Local IDE → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: [CLOUDSQL_INSTANCE_NAME]
- Connection Name: [CLOUDSQL_CONNECTION_NAME]
- Method: Cloud SQL Auth Proxy on localhost

To connect:
1. Start Auth Proxy: ./cloud-sql-proxy CLOUDSQL_CONNECTION_NAME --port=PORT
2. Connect to: 127.0.0.1:PORT

Alternative: Use Cloud SQL Connector libraries (no proxy needed)

Next steps:
1. Store credentials in environment variables
2. Add .env to .gitignore
3. Test connection from your application
```
