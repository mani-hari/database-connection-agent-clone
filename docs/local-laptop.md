# Cloud SQL Connection: Local Laptop / Development Machine

This instruction set guides connecting your local development machine to Cloud SQL for development and testing purposes.

---

## Overview

Connecting from a local machine requires the **Cloud SQL Auth Proxy** because:
- Your laptop's IP is typically dynamic (changes frequently)
- Home/office networks are behind NAT
- Auth Proxy provides secure, encrypted connections without exposing Cloud SQL to the internet

---

## Prerequisites Check

```bash
# Verify Google Cloud SDK is installed
gcloud version

# Verify authentication
gcloud auth list

# Login if needed
gcloud auth login

# Also login for application default credentials
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify project
gcloud config get-value project
```

---

## STEP 1: Gather Cloud SQL Instance Information

### 1.1 List Available Instances

```bash
# List all Cloud SQL instances in your project
gcloud sql instances list --format="table(name,databaseVersion,region,state)"
```

**User prompt:** "Which Cloud SQL instance do you want to connect to?"

### 1.2 Get Instance Details

```bash
# Store instance name
CLOUD_SQL_INSTANCE="your-instance-name"

# Get connection details
gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="yaml(name,connectionName,ipAddresses,region,databaseVersion)"

# Extract connection name (you'll need this)
CONNECTION_NAME=$(gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="value(connectionName)")
echo "Connection Name: ${CONNECTION_NAME}"
```

**Store these values:**
- `CONNECTION_NAME`: Format `project:region:instance`
- `REGION`: Instance region
- `DB_VERSION`: postgresql, mysql, or sqlserver

### 1.3 Get Database Credentials

```
User prompts:
- "What is your database name?" → DB_NAME
- "What is your database username?" → DB_USER
- "What is your database password?" → DB_PASSWORD (handle securely)
```

---

## STEP 2: Install Cloud SQL Auth Proxy

### macOS

```bash
# Using Homebrew (recommended)
brew install cloud-sql-proxy

# Or download directly
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.19.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Linux

```bash
# Download for Linux AMD64
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.19.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/

# For Linux ARM64
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.19.0/cloud-sql-proxy.linux.arm64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Windows

```powershell
# Download for Windows
Invoke-WebRequest -Uri "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.19.0/cloud-sql-proxy.x64.exe" -OutFile "cloud-sql-proxy.exe"

# Add to PATH or move to a directory in PATH
Move-Item cloud-sql-proxy.exe C:\Windows\System32\
```

### Verify Installation

```bash
cloud-sql-proxy --version
```

---

## STEP 3: Ensure IAM Permissions

Your Google Cloud user account (or service account) needs the **Cloud SQL Client** role:

```bash
# Check current user
gcloud config get-value account

# Grant Cloud SQL Client role (if you have permission to do so)
PROJECT_ID=$(gcloud config get-value project)
USER_EMAIL=$(gcloud config get-value account)

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="user:${USER_EMAIL}" \
    --role="roles/cloudsql.client"
```

If you can't grant yourself permissions, ask your administrator to grant `roles/cloudsql.client`.

---

## STEP 4: Start the Auth Proxy

### 4.1 Basic Start (Development)

Open a terminal window and run:

**For PostgreSQL (port 5432):**
```bash
cloud-sql-proxy --port 5432 ${CONNECTION_NAME}
```

**For MySQL (port 3306):**
```bash
cloud-sql-proxy --port 3306 ${CONNECTION_NAME}
```

**For SQL Server (port 1433):**
```bash
cloud-sql-proxy --port 1433 ${CONNECTION_NAME}
```

**Expected output:**
```
Authorizing with Application Default Credentials
Listening on 127.0.0.1:5432 for project:region:instance
Ready for new connections
```

### 4.2 Run in Background

```bash
# Unix/Mac - run in background
cloud-sql-proxy --port 5432 ${CONNECTION_NAME} &

# Or use nohup for persistence
nohup cloud-sql-proxy --port 5432 ${CONNECTION_NAME} > proxy.log 2>&1 &
```

### 4.3 Alternative: Unix Socket (Mac/Linux)

```bash
# Create socket directory
mkdir -p /tmp/cloudsql

# Start proxy with Unix socket
cloud-sql-proxy --unix-socket /tmp/cloudsql ${CONNECTION_NAME}

# Socket will be at: /tmp/cloudsql/${CONNECTION_NAME}
```

---

## STEP 5: Install Database Client & Test Connection

### 5.1 Install Database Client

**PostgreSQL:**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Verify
psql --version
```

**MySQL:**
```bash
# macOS
brew install mysql-client

# Ubuntu/Debian
sudo apt-get install mysql-client

# Verify
mysql --version
```

### 5.2 Test Connection (Auth Proxy Running)

**Keep the Auth Proxy running in one terminal, open a new terminal for testing.**

**PostgreSQL:**
```bash
psql -h 127.0.0.1 -p 5432 -U ${DB_USER} -d ${DB_NAME}
# Enter password when prompted

# Test queries:
SELECT version();
\dt
\q
```

**MySQL:**
```bash
mysql -h 127.0.0.1 -P 3306 -u ${DB_USER} -p ${DB_NAME}
# Enter password when prompted

# Test queries:
SELECT VERSION();
SHOW DATABASES;
exit
```

**SQL Server:**
```bash
# Install sqlcmd first
# macOS: brew install microsoft/mssql-release/mssql-tools

sqlcmd -S 127.0.0.1,1433 -U ${DB_USER} -P ${DB_PASSWORD} -d ${DB_NAME}

# Test query:
SELECT @@VERSION;
GO
```

### 5.3 Verify Connection Success

```
✅ Connection successful!
   - Database server version displayed
   - Can run queries
   - No connection errors

❌ Connection failed:
   - Check Auth Proxy is running
   - Verify credentials
   - Check IAM permissions
   - Ensure correct port
```

---

## STEP 6: Generate Application Code

### Ask Programming Language

```
What programming language is your application written in?
1. Python
2. Node.js
3. Java
4. Go
5. PHP
6. Ruby
```

---

### Python

**Install dependencies:**
```bash
pip install sqlalchemy cloud-sql-python-connector pg8000 pymysql
```

**Option A: Using Cloud SQL Python Connector (Recommended)**

The connector handles the proxy connection automatically:

```python
# PostgreSQL
import sqlalchemy
from google.cloud.sql.connector import Connector

def connect_with_connector():
    connector = Connector()

    def getconn():
        return connector.connect(
            "${CONNECTION_NAME}",  # project:region:instance
            "pg8000",
            user="${DB_USER}",
            password="${DB_PASSWORD}",
            db="${DB_NAME}",
        )

    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
    return engine, connector

# Usage
engine, connector = connect_with_connector()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
connector.close()
```

```python
# MySQL
import sqlalchemy
from google.cloud.sql.connector import Connector

def connect_with_connector():
    connector = Connector()

    def getconn():
        return connector.connect(
            "${CONNECTION_NAME}",
            "pymysql",
            user="${DB_USER}",
            password="${DB_PASSWORD}",
            db="${DB_NAME}",
        )

    engine = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
    )
    return engine, connector
```

**Option B: Using Local Auth Proxy**

If Auth Proxy is running locally:

```python
# PostgreSQL with psycopg2
import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    database="${DB_NAME}",
    user="${DB_USER}",
    password="${DB_PASSWORD}"
)

cursor = conn.cursor()
cursor.execute("SELECT version()")
print(cursor.fetchone())
conn.close()
```

```python
# MySQL with pymysql
import pymysql

conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    database="${DB_NAME}",
    user="${DB_USER}",
    password="${DB_PASSWORD}"
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION()")
print(cursor.fetchone())
conn.close()
```

---

### Node.js

**Install dependencies:**
```bash
npm install pg mysql2 @google-cloud/cloud-sql-connector
```

**Option A: Using Cloud SQL Node.js Connector**

```javascript
// PostgreSQL
const { Connector } = require('@google-cloud/cloud-sql-connector');
const { Pool } = require('pg');

async function connectWithConnector() {
    const connector = new Connector();
    const clientOpts = await connector.getOptions({
        instanceConnectionName: '${CONNECTION_NAME}',
    });

    const pool = new Pool({
        ...clientOpts,
        user: '${DB_USER}',
        password: '${DB_PASSWORD}',
        database: '${DB_NAME}',
    });

    const result = await pool.query('SELECT NOW()');
    console.log('Connected!', result.rows);

    await pool.end();
    connector.close();
}

connectWithConnector();
```

**Option B: Using Local Auth Proxy**

```javascript
// PostgreSQL
const { Pool } = require('pg');

const pool = new Pool({
    host: '127.0.0.1',
    port: 5432,
    database: '${DB_NAME}',
    user: '${DB_USER}',
    password: '${DB_PASSWORD}',
});

pool.query('SELECT NOW()', (err, res) => {
    console.log(res.rows);
    pool.end();
});
```

```javascript
// MySQL
const mysql = require('mysql2/promise');

async function connect() {
    const conn = await mysql.createConnection({
        host: '127.0.0.1',
        port: 3306,
        database: '${DB_NAME}',
        user: '${DB_USER}',
        password: '${DB_PASSWORD}',
    });

    const [rows] = await conn.execute('SELECT VERSION()');
    console.log(rows);
    await conn.end();
}

connect();
```

---

### Java

**Maven dependencies:**
```xml
<!-- For connector-based connection -->
<dependency>
    <groupId>com.google.cloud.sql</groupId>
    <artifactId>postgres-socket-factory</artifactId>
    <version>1.15.0</version>
</dependency>

<!-- Database driver -->
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>postgresql</artifactId>
    <version>42.6.0</version>
</dependency>
```

**Using Cloud SQL JDBC Socket Factory:**

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class CloudSQLConnection {
    public static void main(String[] args) throws Exception {
        // Using socket factory (handles connection automatically)
        String jdbcUrl = String.format(
            "jdbc:postgresql:///${DB_NAME}?" +
            "cloudSqlInstance=${CONNECTION_NAME}&" +
            "socketFactory=com.google.cloud.sql.postgres.SocketFactory&" +
            "user=${DB_USER}&" +
            "password=${DB_PASSWORD}"
        );

        try (Connection conn = DriverManager.getConnection(jdbcUrl);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT version()")) {
            while (rs.next()) {
                System.out.println(rs.getString(1));
            }
        }
    }
}
```

**Using Local Auth Proxy:**

```java
String jdbcUrl = "jdbc:postgresql://127.0.0.1:5432/${DB_NAME}";
Connection conn = DriverManager.getConnection(jdbcUrl, "${DB_USER}", "${DB_PASSWORD}");
```

---

### Go

**Install dependencies:**
```bash
go get cloud.google.com/go/cloudsqlconn
go get github.com/jackc/pgx/v5
```

**Using Cloud SQL Go Connector:**

```go
package main

import (
    "context"
    "database/sql"
    "log"
    "net"

    "cloud.google.com/go/cloudsqlconn"
    "github.com/jackc/pgx/v5"
    "github.com/jackc/pgx/v5/stdlib"
)

func main() {
    ctx := context.Background()

    d, err := cloudsqlconn.NewDialer(ctx)
    if err != nil {
        log.Fatal(err)
    }
    defer d.Close()

    dsn := "user=${DB_USER} password=${DB_PASSWORD} dbname=${DB_NAME}"
    config, err := pgx.ParseConfig(dsn)
    if err != nil {
        log.Fatal(err)
    }

    config.DialFunc = func(ctx context.Context, network, addr string) (net.Conn, error) {
        return d.Dial(ctx, "${CONNECTION_NAME}")
    }

    dbURI := stdlib.RegisterConnConfig(config)
    db, err := sql.Open("pgx", dbURI)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    var version string
    err = db.QueryRow("SELECT version()").Scan(&version)
    if err != nil {
        log.Fatal(err)
    }
    log.Println("Connected:", version)
}
```

---

## STEP 7: Development Workflow Tips

### 7.1 Environment Variables

Store credentials in environment variables:

```bash
# .env file (DON'T commit this!)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
CLOUD_SQL_CONNECTION_NAME=project:region:instance
```

### 7.2 VS Code Integration

Add to `.vscode/tasks.json`:
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Cloud SQL Proxy",
            "type": "shell",
            "command": "cloud-sql-proxy --port 5432 ${CLOUD_SQL_CONNECTION_NAME}",
            "isBackground": true,
            "problemMatcher": []
        }
    ]
}
```

### 7.3 Make/Script Helper

Create a `Makefile`:
```makefile
.PHONY: proxy db-connect

proxy:
	cloud-sql-proxy --port 5432 ${CONNECTION_NAME}

db-connect:
	psql -h 127.0.0.1 -p 5432 -U ${DB_USER} -d ${DB_NAME}
```

---

## STEP 8: Security Best Practices

✅ **Never commit credentials** - Use environment variables or Secret Manager
✅ **Use Application Default Credentials** - `gcloud auth application-default login`
✅ **Rotate passwords regularly** - Update in Secret Manager
✅ **Use IAM database authentication** - When supported by your database version
✅ **Limit IAM permissions** - Only grant `roles/cloudsql.client` to developers who need it

---

## Troubleshooting

### Auth Proxy won't start

```bash
# Check if port is in use
lsof -i :5432  # or netstat -an | grep 5432

# Kill existing process
pkill cloud-sql-proxy

# Try different port
cloud-sql-proxy --port 15432 ${CONNECTION_NAME}
```

### Permission denied

```bash
# Re-authenticate
gcloud auth application-default login

# Verify role
gcloud projects get-iam-policy $(gcloud config get-value project) \
    --filter="bindings.members:user:$(gcloud config get-value account)" \
    --format="table(bindings.role)"
```

### Connection timeout

```bash
# Check if proxy is listening
curl -v telnet://127.0.0.1:5432

# Check proxy logs
cloud-sql-proxy --port 5432 ${CONNECTION_NAME} 2>&1 | tee proxy.log
```

---

## Success!

🎉 Your local laptop is now connected to Cloud SQL!

**Summary:**
- Cloud SQL Instance: `${CLOUD_SQL_INSTANCE}`
- Connection Name: `${CONNECTION_NAME}`
- Local Connection: `127.0.0.1:5432` (via Auth Proxy)
- Method: Cloud SQL Auth Proxy (Secure)

**Next Steps:**
- Start developing your application
- Consider setting up CI/CD with Cloud SQL connections
- Use Secret Manager for production credentials
