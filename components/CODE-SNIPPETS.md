# Cloud SQL Connection Code Snippets

This document provides a consolidated library of Cloud SQL connection code snippets organized by database type, connection method, and programming language.

## Quick Reference: Connection Methods by Compute Type

| Connection Method | Local IDE | GCE VM | Cloud Run | GKE | Description |
|------------------|-----------|---------|-----------|-----|-------------|
| **TCP/IP to 127.0.0.1** (Auth Proxy) | ✅ | ✅ | ❌ | ✅ | Requires Cloud SQL Auth Proxy running locally or as sidecar |
| **TCP/IP to Private IP** | ❌ | ✅ | ✅* | ❌ | Direct connection to Cloud SQL private IP (requires VPC) |
| **Unix Socket** | ❌ | ❌ | ✅ | ❌ | Cloud Run built-in Cloud SQL connection |
| **Cloud SQL Connector Library** | ✅ | ✅ | ✅ | ✅ | Library-based connection (no proxy binary needed) |

*Cloud Run requires VPC Connector or Direct VPC Egress for private IP connections.

---

## Table of Contents

1. [PostgreSQL Connections](#postgresql-connections)
   - [TCP/IP (Auth Proxy at 127.0.0.1)](#postgresql-tcpip-auth-proxy)
   - [TCP/IP (Private IP)](#postgresql-tcpip-private-ip)
   - [Unix Socket](#postgresql-unix-socket)
   - [Cloud SQL Connector Library](#postgresql-cloud-sql-connector)

2. [MySQL Connections](#mysql-connections)
   - [TCP/IP (Auth Proxy at 127.0.0.1)](#mysql-tcpip-auth-proxy)
   - [TCP/IP (Private IP)](#mysql-tcpip-private-ip)
   - [Unix Socket](#mysql-unix-socket)
   - [Cloud SQL Connector Library](#mysql-cloud-sql-connector)

3. [SQL Server Connections](#sql-server-connections)
   - [TCP/IP (Auth Proxy at 127.0.0.1)](#sql-server-tcpip-auth-proxy)
   - [TCP/IP (Private IP)](#sql-server-tcpip-private-ip)

---

# PostgreSQL Connections

## PostgreSQL: TCP/IP (Auth Proxy)

**Use case:** Local development, GKE sidecar pattern
**Compute types:** Local IDE, GCE VM, GKE
**Requirements:** Cloud SQL Auth Proxy running on 127.0.0.1:5432

### Python

```python
import sqlalchemy

def connect_via_proxy():
    """Connect to PostgreSQL via Cloud SQL Auth Proxy on localhost"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"

    # Auth Proxy runs on localhost:5432
    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            host="127.0.0.1",
            port=5432,
            database=db_name,
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_via_proxy()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `sqlalchemy`, `pg8000`

### Node.js

```javascript
// Connect to PostgreSQL via Cloud SQL Auth Proxy on localhost
const { Pool } = require('pg');

const pool = new Pool({
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  database: '{{DB_NAME}}',
  host: '127.0.0.1',
  port: 5432,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query, pool };
```

**Dependencies:** `pg`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to PostgreSQL via Cloud SQL Auth Proxy on localhost
    private static final String DB_URL = "jdbc:postgresql://127.0.0.1:5432/{{DB_NAME}}";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** PostgreSQL JDBC Driver

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/lib/pq"
)

// Connect to PostgreSQL via Cloud SQL Auth Proxy on localhost
func connectViaProxy() (*sql.DB, error) {
    dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
        "127.0.0.1", 5432, "{{DB_USER}}", "{{DB_PASS}}", "{{DB_NAME}}")

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/lib/pq`

---

## PostgreSQL: TCP/IP (Private IP)

**Use case:** GCE VM in same VPC, Cloud Run with VPC Connector
**Compute types:** GCE VM, Cloud Run (with VPC)
**Requirements:** Cloud SQL Private IP enabled, same VPC network

### Python

```python
import sqlalchemy

def connect_with_private_ip():
    """Connect to PostgreSQL using Private IP (GCE VM, Cloud Run with VPC)"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"
    db_host = "{{PRIVATE_IP}}"  # Cloud SQL private IP address
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

**Dependencies:** `sqlalchemy`, `pg8000`

### Node.js

```javascript
// Connect to PostgreSQL using Private IP (GCE VM, Cloud Run with VPC)
const { Pool } = require('pg');

const pool = new Pool({
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  database: '{{DB_NAME}}',
  host: '{{PRIVATE_IP}}',  // Cloud SQL private IP address
  port: 5432,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query, pool };
```

**Dependencies:** `pg`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to PostgreSQL using Private IP (GCE VM, Cloud Run with VPC)
    private static final String DB_URL = "jdbc:postgresql://{{PRIVATE_IP}}:5432/{{DB_NAME}}";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** PostgreSQL JDBC Driver

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/lib/pq"
)

// Connect to PostgreSQL using Private IP (GCE VM, Cloud Run with VPC)
func connectWithPrivateIP() (*sql.DB, error) {
    dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
        "{{PRIVATE_IP}}", 5432, "{{DB_USER}}", "{{DB_PASS}}", "{{DB_NAME}}")

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/lib/pq`

---

## PostgreSQL: Unix Socket

**Use case:** Cloud Run serverless applications
**Compute types:** Cloud Run, App Engine
**Requirements:** Cloud Run service configured with `--add-cloudsql-instances`

### Python

```python
import os
import sqlalchemy

def connect_unix_socket():
    """Connect to PostgreSQL via Unix Socket (Cloud Run, App Engine)"""
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]  # project:region:instance

    # Unix socket path for PostgreSQL
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

**Dependencies:** `sqlalchemy`, `pg8000`

### Node.js

```javascript
// Connect to PostgreSQL via Unix Socket (Cloud Run, App Engine)
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  host: `/cloudsql/${process.env.INSTANCE_CONNECTION_NAME}`,  // project:region:instance
  max: 10,
});

async function query(text, params) {
  const res = await pool.query(text, params);
  return res.rows;
}

module.exports = { query, pool };
```

**Dependencies:** `pg`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudRunConnection {
    // Connect to PostgreSQL via Unix Socket (Cloud Run, App Engine)
    public static Connection getConnection() throws SQLException {
        String dbUser = System.getenv("DB_USER");
        String dbPass = System.getenv("DB_PASS");
        String dbName = System.getenv("DB_NAME");
        String instanceConnectionName = System.getenv("INSTANCE_CONNECTION_NAME");  // project:region:instance

        String socketPath = "/cloudsql/" + instanceConnectionName;
        String jdbcUrl = String.format(
            "jdbc:postgresql:///%s?cloudSqlInstance=%s&socketFactory=com.google.cloud.sql.postgres.SocketFactory",
            dbName, instanceConnectionName
        );

        return DriverManager.getConnection(jdbcUrl, dbUser, dbPass);
    }
}
```

**Dependencies:** PostgreSQL JDBC Driver, Cloud SQL Socket Factory

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    "os"

    _ "github.com/jackc/pgx/v4/stdlib"
)

// Connect to PostgreSQL via Unix Socket (Cloud Run, App Engine)
func connectUnixSocket() (*sql.DB, error) {
    var (
        dbUser                 = os.Getenv("DB_USER")
        dbPwd                  = os.Getenv("DB_PASS")
        dbName                 = os.Getenv("DB_NAME")
        instanceConnectionName = os.Getenv("INSTANCE_CONNECTION_NAME")  // project:region:instance
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

**Dependencies:** `github.com/jackc/pgx/v4`

---

## PostgreSQL: Cloud SQL Connector

**Use case:** All compute types, no separate proxy process
**Compute types:** Local IDE, GCE VM, Cloud Run, GKE
**Requirements:** Cloud SQL Connector library installed

### Python

```python
# pip install cloud-sql-python-connector[pg8000]
import os
from google.cloud.sql.connector import Connector
import sqlalchemy

def connect_with_connector():
    """Connect to PostgreSQL using Cloud SQL Connector library (all platforms)"""
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME", "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}")
    db_user = os.environ.get("DB_USER", "{{DB_USER}}")
    db_pass = os.environ.get("DB_PASS", "{{DB_PASS}}")
    db_name = os.environ.get("DB_NAME", "{{DB_NAME}}")

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

# Usage
engine = connect_with_connector()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `cloud-sql-python-connector[pg8000]`, `sqlalchemy`

### Node.js

```javascript
// npm install @google-cloud/cloud-sql-connector
const { Connector } = require('@google-cloud/cloud-sql-connector');

async function connect() {
  // Connect to PostgreSQL using Cloud SQL Connector library (all platforms)
  const connector = new Connector();
  const clientOpts = await connector.getOptions({
    instanceConnectionName: process.env.INSTANCE_CONNECTION_NAME || '{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}',
  });

  const { Pool } = require('pg');
  const pool = new Pool({
    ...clientOpts,
    user: process.env.DB_USER || '{{DB_USER}}',
    password: process.env.DB_PASS || '{{DB_PASS}}',
    database: process.env.DB_NAME || '{{DB_NAME}}',
    max: 10,
  });

  return pool;
}

module.exports = { connect };
```

**Dependencies:** `@google-cloud/cloud-sql-connector`, `pg`

### Java

```java
// Add dependency: com.google.cloud.sql:postgres-socket-factory
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;

public class CloudSQLConnector {
    // Connect to PostgreSQL using Cloud SQL Connector library (all platforms)
    public static DataSource createConnectionPool() {
        HikariConfig config = new HikariConfig();

        config.setJdbcUrl(String.format("jdbc:postgresql:///%s", "{{DB_NAME}}"));
        config.setUsername("{{DB_USER}}");
        config.setPassword("{{DB_PASS}}");

        config.addDataSourceProperty("socketFactory", "com.google.cloud.sql.postgres.SocketFactory");
        config.addDataSourceProperty("cloudSqlInstance", "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}");

        config.setMaximumPoolSize(5);
        config.setMinimumIdle(5);
        config.setConnectionTimeout(10000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        return new HikariDataSource(config);
    }
}
```

**Dependencies:** `com.google.cloud.sql:postgres-socket-factory`, `com.zaxxer:HikariCP`

### Go

```go
// go get cloud.google.com/go/cloudsqlconn
// go get github.com/jackc/pgx/v4
package main

import (
    "context"
    "database/sql"
    "net"

    "cloud.google.com/go/cloudsqlconn"
    "github.com/jackc/pgx/v4"
    "github.com/jackc/pgx/v4/stdlib"
)

// Connect to PostgreSQL using Cloud SQL Connector library (all platforms)
func connectWithConnector() (*sql.DB, error) {
    ctx := context.Background()

    d, err := cloudsqlconn.NewDialer(ctx)
    if err != nil {
        return nil, err
    }

    dsn := "user={{DB_USER}} password={{DB_PASS}} dbname={{DB_NAME}} sslmode=disable"
    config, err := pgx.ParseConfig(dsn)
    if err != nil {
        return nil, err
    }

    config.DialFunc = func(ctx context.Context, network, addr string) (net.Conn, error) {
        return d.Dial(ctx, "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}")
    }

    dbURI := stdlib.RegisterConnConfig(config)
    db, err := sql.Open("pgx", dbURI)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `cloud.google.com/go/cloudsqlconn`, `github.com/jackc/pgx/v4`

---

# MySQL Connections

## MySQL: TCP/IP (Auth Proxy)

**Use case:** Local development, GKE sidecar pattern
**Compute types:** Local IDE, GCE VM, GKE
**Requirements:** Cloud SQL Auth Proxy running on 127.0.0.1:3306

### Python

```python
import sqlalchemy

def connect_via_proxy():
    """Connect to MySQL via Cloud SQL Auth Proxy on localhost"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"

    # Auth Proxy runs on localhost:3306
    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="mysql+pymysql",
            username=db_user,
            password=db_pass,
            host="127.0.0.1",
            port=3306,
            database=db_name,
        ),
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_via_proxy()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `sqlalchemy`, `pymysql`

### Node.js

```javascript
// Connect to MySQL via Cloud SQL Auth Proxy on localhost
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: '127.0.0.1',
  port: 3306,
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  database: '{{DB_NAME}}',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = { pool };
```

**Dependencies:** `mysql2`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to MySQL via Cloud SQL Auth Proxy on localhost
    private static final String DB_URL = "jdbc:mysql://127.0.0.1:3306/{{DB_NAME}}";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** MySQL Connector/J

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/go-sql-driver/mysql"
)

// Connect to MySQL via Cloud SQL Auth Proxy on localhost
func connectViaProxy() (*sql.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
        "{{DB_USER}}", "{{DB_PASS}}", "127.0.0.1", 3306, "{{DB_NAME}}")

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/go-sql-driver/mysql`

---

## MySQL: TCP/IP (Private IP)

**Use case:** GCE VM in same VPC, Cloud Run with VPC Connector
**Compute types:** GCE VM, Cloud Run (with VPC)
**Requirements:** Cloud SQL Private IP enabled, same VPC network

### Python

```python
import sqlalchemy

def connect_with_private_ip():
    """Connect to MySQL using Private IP (GCE VM, Cloud Run with VPC)"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"
    db_host = "{{PRIVATE_IP}}"  # Cloud SQL private IP address
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

# Usage
engine = connect_with_private_ip()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `sqlalchemy`, `pymysql`

### Node.js

```javascript
// Connect to MySQL using Private IP (GCE VM, Cloud Run with VPC)
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: '{{PRIVATE_IP}}',  // Cloud SQL private IP address
  port: 3306,
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  database: '{{DB_NAME}}',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = { pool };
```

**Dependencies:** `mysql2`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to MySQL using Private IP (GCE VM, Cloud Run with VPC)
    private static final String DB_URL = "jdbc:mysql://{{PRIVATE_IP}}:3306/{{DB_NAME}}";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** MySQL Connector/J

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/go-sql-driver/mysql"
)

// Connect to MySQL using Private IP (GCE VM, Cloud Run with VPC)
func connectWithPrivateIP() (*sql.DB, error) {
    dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
        "{{DB_USER}}", "{{DB_PASS}}", "{{PRIVATE_IP}}", 3306, "{{DB_NAME}}")

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/go-sql-driver/mysql`

---

## MySQL: Unix Socket

**Use case:** Cloud Run serverless applications
**Compute types:** Cloud Run, App Engine
**Requirements:** Cloud Run service configured with `--add-cloudsql-instances`

### Python

```python
import os
import sqlalchemy

def connect_unix_socket():
    """Connect to MySQL via Unix Socket (Cloud Run, App Engine)"""
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_name = os.environ["DB_NAME"]
    instance_connection_name = os.environ["INSTANCE_CONNECTION_NAME"]  # project:region:instance

    # Unix socket path for MySQL
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

# Usage
engine = connect_unix_socket()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `sqlalchemy`, `pymysql`

### Node.js

```javascript
// Connect to MySQL via Unix Socket (Cloud Run, App Engine)
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  socketPath: `/cloudsql/${process.env.INSTANCE_CONNECTION_NAME}`,  // project:region:instance
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = { pool };
```

**Dependencies:** `mysql2`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudRunConnection {
    // Connect to MySQL via Unix Socket (Cloud Run, App Engine)
    public static Connection getConnection() throws SQLException {
        String dbUser = System.getenv("DB_USER");
        String dbPass = System.getenv("DB_PASS");
        String dbName = System.getenv("DB_NAME");
        String instanceConnectionName = System.getenv("INSTANCE_CONNECTION_NAME");  // project:region:instance

        String jdbcUrl = String.format(
            "jdbc:mysql:///%s?cloudSqlInstance=%s&socketFactory=com.google.cloud.sql.mysql.SocketFactory",
            dbName, instanceConnectionName
        );

        return DriverManager.getConnection(jdbcUrl, dbUser, dbPass);
    }
}
```

**Dependencies:** MySQL Connector/J, Cloud SQL Socket Factory

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    "os"

    _ "github.com/go-sql-driver/mysql"
)

// Connect to MySQL via Unix Socket (Cloud Run, App Engine)
func connectUnixSocket() (*sql.DB, error) {
    var (
        dbUser                 = os.Getenv("DB_USER")
        dbPwd                  = os.Getenv("DB_PASS")
        dbName                 = os.Getenv("DB_NAME")
        instanceConnectionName = os.Getenv("INSTANCE_CONNECTION_NAME")  // project:region:instance
        socketDir              = "/cloudsql"
    )

    dsn := fmt.Sprintf("%s:%s@unix(%s/%s)/%s",
        dbUser, dbPwd, socketDir, instanceConnectionName, dbName)

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/go-sql-driver/mysql`

---

## MySQL: Cloud SQL Connector

**Use case:** All compute types, no separate proxy process
**Compute types:** Local IDE, GCE VM, Cloud Run, GKE
**Requirements:** Cloud SQL Connector library installed

### Python

```python
# pip install cloud-sql-python-connector[pymysql]
import os
from google.cloud.sql.connector import Connector
import sqlalchemy

def connect_with_connector():
    """Connect to MySQL using Cloud SQL Connector library (all platforms)"""
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME", "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}")
    db_user = os.environ.get("DB_USER", "{{DB_USER}}")
    db_pass = os.environ.get("DB_PASS", "{{DB_PASS}}")
    db_name = os.environ.get("DB_NAME", "{{DB_NAME}}")

    connector = Connector()

    def getconn():
        conn = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_with_connector()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `cloud-sql-python-connector[pymysql]`, `sqlalchemy`

### Node.js

```javascript
// npm install @google-cloud/cloud-sql-connector
const { Connector } = require('@google-cloud/cloud-sql-connector');

async function connect() {
  // Connect to MySQL using Cloud SQL Connector library (all platforms)
  const connector = new Connector();
  const clientOpts = await connector.getOptions({
    instanceConnectionName: process.env.INSTANCE_CONNECTION_NAME || '{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}',
    ipType: 'PUBLIC',  // or 'PRIVATE'
  });

  const mysql = require('mysql2/promise');
  const pool = mysql.createPool({
    ...clientOpts,
    user: process.env.DB_USER || '{{DB_USER}}',
    password: process.env.DB_PASS || '{{DB_PASS}}',
    database: process.env.DB_NAME || '{{DB_NAME}}',
  });

  return pool;
}

module.exports = { connect };
```

**Dependencies:** `@google-cloud/cloud-sql-connector`, `mysql2`

### Java

```java
// Add dependency: com.google.cloud.sql:mysql-socket-factory-connector-j-8
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import javax.sql.DataSource;

public class CloudSQLConnector {
    // Connect to MySQL using Cloud SQL Connector library (all platforms)
    public static DataSource createConnectionPool() {
        HikariConfig config = new HikariConfig();

        config.setJdbcUrl(String.format("jdbc:mysql:///%s", "{{DB_NAME}}"));
        config.setUsername("{{DB_USER}}");
        config.setPassword("{{DB_PASS}}");

        config.addDataSourceProperty("socketFactory", "com.google.cloud.sql.mysql.SocketFactory");
        config.addDataSourceProperty("cloudSqlInstance", "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}");

        config.setMaximumPoolSize(5);
        config.setMinimumIdle(5);
        config.setConnectionTimeout(10000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        return new HikariDataSource(config);
    }
}
```

**Dependencies:** `com.google.cloud.sql:mysql-socket-factory-connector-j-8`, `com.zaxxer:HikariCP`

### Go

```go
// go get cloud.google.com/go/cloudsqlconn
// go get github.com/go-sql-driver/mysql
package main

import (
    "context"
    "database/sql"
    "fmt"
    "net"

    "cloud.google.com/go/cloudsqlconn"
    "github.com/go-sql-driver/mysql"
)

// Connect to MySQL using Cloud SQL Connector library (all platforms)
func connectWithConnector() (*sql.DB, error) {
    ctx := context.Background()

    d, err := cloudsqlconn.NewDialer(ctx)
    if err != nil {
        return nil, err
    }

    mysql.RegisterDialContext("cloudsql", func(ctx context.Context, addr string) (net.Conn, error) {
        return d.Dial(ctx, "{{PROJECT_ID}}:{{REGION}}:{{INSTANCE_NAME}}")
    })

    dsn := fmt.Sprintf("%s:%s@cloudsql(localhost)/%s",
        "{{DB_USER}}", "{{DB_PASS}}", "{{DB_NAME}}")

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `cloud.google.com/go/cloudsqlconn`, `github.com/go-sql-driver/mysql`

---

# SQL Server Connections

## SQL Server: TCP/IP (Auth Proxy)

**Use case:** Local development, GKE sidecar pattern
**Compute types:** Local IDE, GCE VM, GKE
**Requirements:** Cloud SQL Auth Proxy running on 127.0.0.1:1433

### Python

```python
import sqlalchemy

def connect_via_proxy():
    """Connect to SQL Server via Cloud SQL Auth Proxy on localhost"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"

    # Auth Proxy runs on localhost:1433
    connection_string = (
        f"mssql+pymssql://{db_user}:{db_pass}@127.0.0.1:1433/{db_name}"
    )

    pool = sqlalchemy.create_engine(
        connection_string,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool

# Usage
engine = connect_via_proxy()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Dependencies:** `sqlalchemy`, `pymssql`

### Node.js

```javascript
// Connect to SQL Server via Cloud SQL Auth Proxy on localhost
const sql = require('mssql');

const config = {
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  server: '127.0.0.1',
  port: 1433,
  database: '{{DB_NAME}}',
  pool: {
    max: 10,
    min: 0,
    idleTimeoutMillis: 30000
  },
  options: {
    encrypt: false,
    trustServerCertificate: true
  }
};

async function connect() {
  const pool = await sql.connect(config);
  return pool;
}

module.exports = { connect };
```

**Dependencies:** `mssql`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to SQL Server via Cloud SQL Auth Proxy on localhost
    private static final String DB_URL = "jdbc:sqlserver://127.0.0.1:1433;databaseName={{DB_NAME}};encrypt=false";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** Microsoft SQL Server JDBC Driver

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/denisenkom/go-mssqldb"
)

// Connect to SQL Server via Cloud SQL Auth Proxy on localhost
func connectViaProxy() (*sql.DB, error) {
    connString := fmt.Sprintf("server=%s;port=%d;user id=%s;password=%s;database=%s;encrypt=disable",
        "127.0.0.1", 1433, "{{DB_USER}}", "{{DB_PASS}}", "{{DB_NAME}}")

    db, err := sql.Open("sqlserver", connString)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/denisenkom/go-mssqldb`

---

## SQL Server: TCP/IP (Private IP)

**Use case:** GCE VM in same VPC, Cloud Run with VPC Connector
**Compute types:** GCE VM, Cloud Run (with VPC)
**Requirements:** Cloud SQL Private IP enabled, same VPC network

### Python

```python
import sqlalchemy

def connect_with_private_ip():
    """Connect to SQL Server using Private IP (GCE VM, Cloud Run with VPC)"""
    db_user = "{{DB_USER}}"
    db_pass = "{{DB_PASS}}"
    db_name = "{{DB_NAME}}"
    db_host = "{{PRIVATE_IP}}"  # Cloud SQL private IP address

    connection_string = (
        f"mssql+pymssql://{db_user}:{db_pass}@{db_host}:1433/{db_name}"
    )

    pool = sqlalchemy.create_engine(
        connection_string,
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

**Dependencies:** `sqlalchemy`, `pymssql`

### Node.js

```javascript
// Connect to SQL Server using Private IP (GCE VM, Cloud Run with VPC)
const sql = require('mssql');

const config = {
  user: '{{DB_USER}}',
  password: '{{DB_PASS}}',
  server: '{{PRIVATE_IP}}',  // Cloud SQL private IP address
  port: 1433,
  database: '{{DB_NAME}}',
  pool: {
    max: 10,
    min: 0,
    idleTimeoutMillis: 30000
  },
  options: {
    encrypt: false,
    trustServerCertificate: true
  }
};

async function connect() {
  const pool = await sql.connect(config);
  return pool;
}

module.exports = { connect };
```

**Dependencies:** `mssql`

### Java

```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    // Connect to SQL Server using Private IP (GCE VM, Cloud Run with VPC)
    private static final String DB_URL = "jdbc:sqlserver://{{PRIVATE_IP}}:1433;databaseName={{DB_NAME}};encrypt=false";
    private static final String USER = "{{DB_USER}}";
    private static final String PASS = "{{DB_PASS}}";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Dependencies:** Microsoft SQL Server JDBC Driver

### Go

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/denisenkom/go-mssqldb"
)

// Connect to SQL Server using Private IP (GCE VM, Cloud Run with VPC)
func connectWithPrivateIP() (*sql.DB, error) {
    connString := fmt.Sprintf("server=%s;port=%d;user id=%s;password=%s;database=%s;encrypt=disable",
        "{{PRIVATE_IP}}", 1433, "{{DB_USER}}", "{{DB_PASS}}", "{{DB_NAME}}")

    db, err := sql.Open("sqlserver", connString)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}
```

**Dependencies:** `github.com/denisenkom/go-mssqldb`

---

## Placeholder Reference

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{DB_USER}}` | Database username | `postgres` or `root` |
| `{{DB_PASS}}` | Database password | `your-secure-password` |
| `{{DB_NAME}}` | Database name | `myapp_db` |
| `{{PRIVATE_IP}}` | Cloud SQL private IP address | `10.1.2.3` |
| `{{HOST}}` | Database host (localhost or IP) | `127.0.0.1` or `10.1.2.3` |
| `{{PORT}}` | Database port | `5432`, `3306`, or `1433` |
| `{{PROJECT_ID}}` | GCP project ID | `my-gcp-project` |
| `{{REGION}}` | Cloud SQL region | `us-central1` |
| `{{INSTANCE_NAME}}` | Cloud SQL instance name | `my-postgres-instance` |
| `{{CONNECTION_NAME}}` | Full connection name | `my-project:us-central1:my-instance` |

---

## Connection Pooling Best Practices

### Recommended Pool Settings

| Platform | pool_size | max_overflow | pool_recycle | Notes |
|----------|-----------|--------------|--------------|-------|
| **Local IDE** | 5 | 2 | 1800 | Small pool for development |
| **GCE VM** | 5-20 | 2-10 | 1800 | Depends on application load |
| **Cloud Run** | 5 | 2 | 1800 | Keep small, scales to zero |
| **GKE** | 5-10 | 2-5 | 1800 | Per pod, multiply by replicas |

### Connection Lifecycle

- `pool_size`: Maximum number of permanent connections
- `max_overflow`: Additional connections when pool is full
- `pool_timeout`: Seconds to wait for connection from pool (30s)
- `pool_recycle`: Seconds before recycling connections (1800s = 30 min)

### Cloud SQL Limits

- **PostgreSQL:** Default max_connections = 100 (varies by tier)
- **MySQL:** Default max_connections = 151 (varies by tier)
- **SQL Server:** Default max_connections = 32767

**Important:** Total connections across all clients must not exceed Cloud SQL instance limits.

---

## Security Best Practices

1. **Never hardcode credentials** - Use environment variables or Secret Manager
2. **Use IAM authentication** when possible (PostgreSQL and MySQL support it)
3. **Prefer Private IP** over Public IP for production workloads
4. **Enable SSL/TLS** for public IP connections
5. **Use Cloud SQL Connector libraries** for automatic credential rotation
6. **Rotate passwords regularly** and store them in Secret Manager
7. **Apply principle of least privilege** - grant minimal database permissions

---

## Troubleshooting

### Common Connection Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Firewall or network issue | Check VPC firewall rules, Private Google Access |
| Authentication failed | Wrong credentials | Verify username/password, check IAM permissions |
| Too many connections | Pool size too large | Reduce pool_size or increase Cloud SQL max_connections |
| Connection reset | Stale connection | Set pool_recycle to 1800 seconds |
| Unix socket not found | Cloud SQL not configured | Add `--add-cloudsql-instances` to Cloud Run deployment |
| Private IP not reachable | Not in same VPC | Enable Private Services Access, verify VPC peering |

### Debug Commands

```bash
# Test PostgreSQL connectivity
psql "host={{HOST}} port={{PORT}} user={{DB_USER}} dbname={{DB_NAME}}"

# Test MySQL connectivity
mysql -h {{HOST}} -P {{PORT}} -u {{DB_USER}} -p {{DB_NAME}}

# Test SQL Server connectivity
sqlcmd -S {{HOST}},{{PORT}} -U {{DB_USER}} -P {{DB_PASS}} -d {{DB_NAME}}

# Check Cloud SQL Auth Proxy logs
./cloud-sql-proxy {{CONNECTION_NAME}} --port={{PORT}} -v

# Test connection from GCE VM
gcloud compute ssh {{VM_NAME}} --zone={{ZONE}} --command="nc -zv {{PRIVATE_IP}} {{PORT}}"
```

---

## Additional Resources

- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy)
- [Cloud SQL Connector Libraries](https://cloud.google.com/sql/docs/mysql/connect-connectors)
- [Best practices for Cloud SQL](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Managing database connections](https://cloud.google.com/sql/docs/mysql/manage-connections)
