# Local IDE / Laptop → Cloud SQL Connection Guide

**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Component References:**
- UI patterns: See `../components/UI-CARDS.md` for ASCII card templates
- Code snippets: See `../components/CODE-SNIPPETS.md` for connection code
- Validation logic: See `../components/NETWORK-VALIDATION.md` for shared checks
- Remediation: See `../components/REMEDIATION.md` for common fix procedures

---

## Step 2B: Local Development Setup

**Auto-Complete Mode:** If user selected auto-complete in Step 2.1, skip "Ready to proceed?" prompts and continue directly. Still pause for consent before modifying resources.

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
gcloud sql instances describe {CLOUDSQL_INSTANCE_NAME} --format="yaml(connectionName)"
```

Extract `CLOUDSQL_CONNECTION_NAME` from the connectionName field.

### 3B.2 Network Analysis Output
```
╔══════════════════════════════════════════════════════════════════╗
║                    LOCAL CONNECTION ANALYSIS                      ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: {CLOUDSQL_INSTANCE_NAME}                     ║
║ Connection Name: {CLOUDSQL_CONNECTION_NAME}                      ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Admin API            │ ✅ / ❌  │ {Enabled/Disabled}    ║
║ Application Default Creds      │ ✅ / ❌  │ {Account email}       ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: Cloud SQL Auth Proxy on localhost                   ║
╚══════════════════════════════════════════════════════════════════╝
```

### 3B.3 Check IAM Permissions (Optional)
Check if user has required permissions. Required role: `roles/cloudsql.client` or `roles/cloudsql.editor`

If needed:
```bash
gcloud projects add-iam-policy-binding {PROJECT_ID} \
  --member="user:{USER_EMAIL}" \
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

Determine the port based on `CLOUDSQL_DATABASE_VERSION`:
- PostgreSQL: 5432
- MySQL: 3306
- SQL Server: 1433

Display the start command:
```
✅ Auth Proxy ready

Run in a separate terminal:
./cloud-sql-proxy {CLOUDSQL_CONNECTION_NAME} --port={PORT}

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
Port: {5432/3306/1433 based on database type}
Proxy Connection: {CLOUDSQL_CONNECTION_NAME}
─────────────────────────────────
```

### 4B.2 Test Connection (Optional)

Offer to test connectivity (Auth Proxy must be running):

**PostgreSQL:**
```bash
psql "host=127.0.0.1 port=5432 user=YOUR_USER dbname=YOUR_DB"
```

**MySQL:**
```bash
mysql -h 127.0.0.1 -P 3306 -u YOUR_USER -p YOUR_DB
```

### 4B.3 Connection Code

Based on `CLOUDSQL_DATABASE_VERSION`, provide the appropriate connection code:

**Python + PostgreSQL:**
```python
import sqlalchemy
import os

def connect_via_proxy():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")

    pool = sqlalchemy.create_engine(
        f"postgresql+pg8000://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}",
        pool_size=5,
        max_overflow=2,
    )
    return pool
```

**Python + MySQL:**
```python
import sqlalchemy
import os

def connect_via_proxy():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")

    pool = sqlalchemy.create_engine(
        f"mysql+pymysql://{db_user}:{db_pass}@127.0.0.1:3306/{db_name}",
        pool_size=5,
        max_overflow=2,
    )
    return pool
```

**Node.js + PostgreSQL:**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: '127.0.0.1',
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
  host: '127.0.0.1',
  port: 3306,
  user: process.env.DB_USER || 'your-db-user',
  password: process.env.DB_PASS || 'your-db-password',
  database: process.env.DB_NAME || 'your-database',
  connectionLimit: 10,
});

module.exports = { pool };
```

### 4B.4 Alternative: Cloud SQL Connector (No Proxy Needed)

Cloud SQL Connector libraries handle connection management automatically without needing a separate proxy process.

**Python + PostgreSQL (Cloud SQL Connector):**
```python
# pip install cloud-sql-python-connector[pg8000]
from google.cloud.sql.connector import Connector
import sqlalchemy
import os

def connect_with_connector():
    connector = Connector()

    def getconn():
        conn = connector.connect(
            "{CLOUDSQL_CONNECTION_NAME}",
            "pg8000",
            user=os.environ.get("DB_USER", "your-db-user"),
            password=os.environ.get("DB_PASS", "your-db-password"),
            db=os.environ.get("DB_NAME", "your-database"),
        )
        return conn

    pool = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
    )
    return pool
```

**Python + MySQL (Cloud SQL Connector):**
```python
# pip install cloud-sql-python-connector[pymysql]
from google.cloud.sql.connector import Connector
import sqlalchemy
import os

def connect_with_connector():
    connector = Connector()

    def getconn():
        conn = connector.connect(
            "{CLOUDSQL_CONNECTION_NAME}",
            "pymysql",
            user=os.environ.get("DB_USER", "your-db-user"),
            password=os.environ.get("DB_PASS", "your-db-password"),
            db=os.environ.get("DB_NAME", "your-database"),
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
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
    instanceConnectionName: '{CLOUDSQL_CONNECTION_NAME}',
  });

  const { Pool } = require('pg');
  const pool = new Pool({
    ...clientOpts,
    user: process.env.DB_USER || 'your-db-user',
    password: process.env.DB_PASS || 'your-db-password',
    database: process.env.DB_NAME || 'your-database',
    max: 10,
  });

  return pool;
}

module.exports = { connect };
```

**Benefits of Cloud SQL Connector:**
- No separate proxy process needed
- Automatic IAM authentication support
- Built-in connection management
- Simpler deployment

---

## Completion

Display:
```
✅ Local IDE → Cloud SQL connection setup complete!

Summary:
- Cloud SQL: {CLOUDSQL_INSTANCE_NAME}
- Connection Name: {CLOUDSQL_CONNECTION_NAME}

Two connection methods available:

Option 1 - Cloud SQL Auth Proxy:
  1. Start proxy: ./cloud-sql-proxy {CLOUDSQL_CONNECTION_NAME} --port={PORT}
  2. Connect to: 127.0.0.1:{PORT}

Option 2 - Cloud SQL Connector (recommended):
  - No separate proxy needed
  - Use language-specific connector library
  - Automatic connection management

💡 Tip: Store credentials as environment variables (add .env to .gitignore)
```
