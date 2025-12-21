# {{COMPUTE_TYPE}} → Cloud SQL Connection Guide

This file contains the complete instructions for connecting {{COMPUTE_DESCRIPTION}} to Cloud SQL.
**Prerequisites:** User has completed Step 0 (Authentication) and Step 1 (Cloud SQL Selection) from GEMINI.md.

**Variables available from previous steps:**
- `PROJECT_ID` - GCP project ID
- `USER_EMAIL` - Authenticated user email
- `CLOUDSQL_INSTANCE_NAME` - Selected Cloud SQL instance
- `CLOUDSQL_REGION` - Cloud SQL region
- `CLOUDSQL_DATABASE_VERSION` - Database type (POSTGRES_XX, MYSQL_X_X, SQLSERVER_XXXX)

---

## Step 2{{STEP_LETTER}}: {{RESOURCE_SELECTION_TITLE}}

### 2{{STEP_LETTER}}.1 Display Loading Message
```
{{LOADING_MESSAGE}}
```

### 2{{STEP_LETTER}}.2 List {{RESOURCE_TYPE}}
```bash
{{GCLOUD_LIST_COMMAND}}
```

### 2{{STEP_LETTER}}.3 User Selection
Present {{RESOURCE_TYPE_PLURAL}} as numbered list. Accept number or name input.

Capture and store:
- `{{PRIMARY_RESOURCE_VAR}}` - {{PRIMARY_RESOURCE_DESCRIPTION}}
- `{{SECONDARY_RESOURCE_VAR}}` - {{SECONDARY_RESOURCE_DESCRIPTION}}
{{ADDITIONAL_VARIABLES}}

Display confirmation:
```
✅ Selected {{RESOURCE_TYPE}}: [{{PRIMARY_RESOURCE_VAR}}] {{CONFIRMATION_DETAILS}}
{{ADDITIONAL_CONFIRMATION_LINES}}
```

**→ Ask: "Ready to proceed to Step 3 (Network Validation)? (yes/no)"**

---

## Step 3{{STEP_LETTER}}: {{NETWORK_VALIDATION_TITLE}}

### 3{{STEP_LETTER}}.1 Gather Cloud SQL Details
```bash
gcloud sql instances describe CLOUDSQL_INSTANCE_NAME --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,settings.ipConfiguration.authorizedNetworks,region)"
```

Extract and store:
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork)
- `CLOUDSQL_CONNECTION_NAME` (format: project:region:instance)

### 3{{STEP_LETTER}}.2 Gather {{RESOURCE_TYPE}} Details
```bash
{{GCLOUD_DESCRIBE_COMMAND}}
```

Extract and store:
{{RESOURCE_SPECIFIC_VARIABLES}}

### 3{{STEP_LETTER}}.3 Network Analysis Output
Display results in this exact format:

```
╔══════════════════════════════════════════════════════════════════╗
║                    {{NETWORK_ANALYSIS_HEADER}}                    ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]                      ║
║ {{RESOURCE_TYPE}}: [{{PRIMARY_RESOURCE_VAR}}]                     ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅ / ❌  │ [IP or "Not enabled"] ║
║ Cloud SQL Public IP            │ ✅ / ❌  │ [IP or "Not enabled"] ║
{{RESOURCE_SPECIFIC_CHECKS}}
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED CONNECTION METHOD: {{CONNECTION_METHOD_OPTIONS}}     ║
╚══════════════════════════════════════════════════════════════════╝
```

**See components/NETWORK-VALIDATION.md for detailed network validation logic.**

### 3{{STEP_LETTER}}.4 Connectivity Decision Tree

{{DECISION_TREE_LOGIC}}

**Example Decision Trees:**

**If Private IP available AND same VPC:**
- Recommend: Direct connection via Private IP
- No additional setup required

**If Private IP available BUT different VPC:**
- Recommend: VPC Peering or move resource to Cloud SQL VPC
- Offer remediation (see 3{{STEP_LETTER}}.5)

**If only Public IP available:**
- Warn: Less secure, recommend enabling Private IP
- Options: Cloud SQL Auth Proxy or Authorized Networks

**If no connectivity path exists:**
- Offer to enable Private IP on Cloud SQL

### 3{{STEP_LETTER}}.5 Remediation Commands (Execute only with user consent)

**See components/REMEDIATION.md for comprehensive remediation options.**

Common remediation patterns:

**Enable Private IP on Cloud SQL:**
```bash
gcloud sql instances patch CLOUDSQL_INSTANCE_NAME \
  --network=projects/PROJECT_ID/global/networks/{{VPC_NAME}} \
  --no-assign-ip
```

**Check Private Services Access:**
```bash
gcloud services vpc-peerings list --network={{VPC_NAME}} --project=PROJECT_ID
```

**Create Private Services Access (if missing):**
```bash
# Step 1: Allocate IP range
gcloud compute addresses create google-managed-services-{{VPC_NAME}} \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network={{VPC_NAME}} \
  --project=PROJECT_ID

# Step 2: Create peering connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-{{VPC_NAME}} \
  --network={{VPC_NAME}} \
  --project=PROJECT_ID
```

{{RESOURCE_SPECIFIC_REMEDIATION}}

After remediation, re-run validation checks.

**→ Ask: "Ready to proceed to Step 4 (Connection Testing and Code)? (yes/no)"**

---

## Step 4{{STEP_LETTER}}: {{CONNECTION_TESTING_TITLE}}

### 4{{STEP_LETTER}}.1 Confirm Connection Details
Display:
```
CONNECTION SUMMARY
─────────────────────────────────
{{RESOURCE_TYPE}}: [{{PRIMARY_RESOURCE_VAR}}]
Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]
Connection Name: [CLOUDSQL_CONNECTION_NAME]
Method: {{CONNECTION_METHOD}}
Host: {{CONNECTION_HOST}}
Port: {{CONNECTION_PORT}} [3306/5432/1433 based on database type]
{{ADDITIONAL_CONNECTION_DETAILS}}
─────────────────────────────────
```

### 4{{STEP_LETTER}}.2 Quick Connectivity Test (Optional)

{{CONNECTIVITY_TEST_COMMANDS}}

Example test commands:

**For PostgreSQL:**
```bash
{{TEST_COMMAND_POSTGRES}}
```

**For MySQL:**
```bash
{{TEST_COMMAND_MYSQL}}
```

**For SQL Server:**
```bash
{{TEST_COMMAND_SQLSERVER}}
```

### 4{{STEP_LETTER}}.3 Language Selection
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

### 4{{STEP_LETTER}}.4 Code Snippets

**See components/CODE-SNIPPETS.md for language-specific connection examples.**

The code snippets should be customized for your connection method:
- **Direct Private IP**: Use `{{CONNECTION_HOST}}:{{CONNECTION_PORT}}`
- **Public IP**: Use `{{CLOUDSQL_PUBLIC_IP}}:{{CONNECTION_PORT}}`
- **Cloud SQL Auth Proxy**: Use `127.0.0.1:{{LOCAL_PORT}}` or Unix socket path
- **Unix Socket (Cloud Run)**: Use `/cloudsql/{{CLOUDSQL_CONNECTION_NAME}}`

#### Python Examples

**Python ({{CONNECTION_METHOD}} - PostgreSQL):**
```python
import os
import sqlalchemy

def connect_to_cloudsql():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")
    db_host = "{{CONNECTION_HOST}}"
    db_port = {{CONNECTION_PORT}}

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
engine = connect_to_cloudsql()
with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())
```

**Python ({{CONNECTION_METHOD}} - MySQL):**
```python
import os
import sqlalchemy

def connect_to_cloudsql():
    db_user = os.environ.get("DB_USER", "your-db-user")
    db_pass = os.environ.get("DB_PASS", "your-db-password")
    db_name = os.environ.get("DB_NAME", "your-database")
    db_host = "{{CONNECTION_HOST}}"
    db_port = {{CONNECTION_PORT}}

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

#### Node.js Examples

**Node.js ({{CONNECTION_METHOD}} - PostgreSQL):**
```javascript
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER || 'your-db-user',
  password: process.env.DB_PASS || 'your-db-password',
  database: process.env.DB_NAME || 'your-database',
  host: '{{CONNECTION_HOST}}',
  port: {{CONNECTION_PORT}},
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

**Node.js ({{CONNECTION_METHOD}} - MySQL):**
```javascript
const mysql = require('mysql2/promise');

const pool = mysql.createPool({
  host: '{{CONNECTION_HOST}}',
  port: {{CONNECTION_PORT}},
  user: process.env.DB_USER || 'your-db-user',
  password: process.env.DB_PASS || 'your-db-password',
  database: process.env.DB_NAME || 'your-database',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

module.exports = { pool };
```

#### Java Examples

**Java ({{CONNECTION_METHOD}} - JDBC PostgreSQL):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    private static final String DB_URL = "jdbc:postgresql://{{CONNECTION_HOST}}:{{CONNECTION_PORT}}/your-database";
    private static final String USER = System.getenv().getOrDefault("DB_USER", "your-db-user");
    private static final String PASS = System.getenv().getOrDefault("DB_PASS", "your-db-password");

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

**Java ({{CONNECTION_METHOD}} - JDBC MySQL):**
```java
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class CloudSQLConnection {
    private static final String DB_URL = "jdbc:mysql://{{CONNECTION_HOST}}:{{CONNECTION_PORT}}/your-database";
    private static final String USER = System.getenv().getOrDefault("DB_USER", "your-db-user");
    private static final String PASS = System.getenv().getOrDefault("DB_PASS", "your-db-password");

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, USER, PASS);
    }
}
```

#### Go Examples

**Go ({{CONNECTION_METHOD}} - PostgreSQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    "os"
    _ "github.com/lib/pq"
)

func connectDB() (*sql.DB, error) {
    dbUser := getEnv("DB_USER", "your-db-user")
    dbPass := getEnv("DB_PASS", "your-db-password")
    dbName := getEnv("DB_NAME", "your-database")
    dbHost := "{{CONNECTION_HOST}}"
    dbPort := "{{CONNECTION_PORT}}"

    dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
        dbHost, dbPort, dbUser, dbPass, dbName)

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}

func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}
```

**Go ({{CONNECTION_METHOD}} - MySQL):**
```go
package main

import (
    "database/sql"
    "fmt"
    "os"
    _ "github.com/go-sql-driver/mysql"
)

func connectDB() (*sql.DB, error) {
    dbUser := getEnv("DB_USER", "your-db-user")
    dbPass := getEnv("DB_PASS", "your-db-password")
    dbName := getEnv("DB_NAME", "your-database")
    dbHost := "{{CONNECTION_HOST}}"
    dbPort := "{{CONNECTION_PORT}}"

    dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s",
        dbUser, dbPass, dbHost, dbPort, dbName)

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        return nil, err
    }

    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    return db, nil
}

func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}
```

#### PHP Examples

**PHP ({{CONNECTION_METHOD}} - PostgreSQL):**
```php
<?php
function connectDB() {
    $host = '{{CONNECTION_HOST}}';
    $port = '{{CONNECTION_PORT}}';
    $dbname = getenv('DB_NAME') ?: 'your-database';
    $user = getenv('DB_USER') ?: 'your-db-user';
    $password = getenv('DB_PASS') ?: 'your-db-password';

    $conn_string = "host=$host port=$port dbname=$dbname user=$user password=$password";

    $conn = pg_connect($conn_string);

    if (!$conn) {
        die("Connection failed");
    }

    return $conn;
}

$db = connectDB();
$result = pg_query($db, "SELECT 1");
$row = pg_fetch_row($result);
print_r($row);
?>
```

**PHP ({{CONNECTION_METHOD}} - MySQL):**
```php
<?php
function connectDB() {
    $host = '{{CONNECTION_HOST}}';
    $port = '{{CONNECTION_PORT}}';
    $dbname = getenv('DB_NAME') ?: 'your-database';
    $user = getenv('DB_USER') ?: 'your-db-user';
    $password = getenv('DB_PASS') ?: 'your-db-password';

    try {
        $pdo = new PDO(
            "mysql:host=$host;port=$port;dbname=$dbname",
            $user,
            $password,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
        return $pdo;
    } catch (PDOException $e) {
        die("Connection failed: " . $e->getMessage());
    }
}

$db = connectDB();
$stmt = $db->query("SELECT 1");
$result = $stmt->fetch();
print_r($result);
?>
```

#### Ruby Examples

**Ruby ({{CONNECTION_METHOD}} - PostgreSQL):**
```ruby
require 'pg'

def connect_db
  PG.connect(
    host: '{{CONNECTION_HOST}}',
    port: {{CONNECTION_PORT}},
    dbname: ENV.fetch('DB_NAME', 'your-database'),
    user: ENV.fetch('DB_USER', 'your-db-user'),
    password: ENV.fetch('DB_PASS', 'your-db-password')
  )
end

conn = connect_db
result = conn.exec('SELECT 1')
puts result.values
conn.close
```

**Ruby ({{CONNECTION_METHOD}} - MySQL):**
```ruby
require 'mysql2'

def connect_db
  Mysql2::Client.new(
    host: '{{CONNECTION_HOST}}',
    port: {{CONNECTION_PORT}},
    database: ENV.fetch('DB_NAME', 'your-database'),
    username: ENV.fetch('DB_USER', 'your-db-user'),
    password: ENV.fetch('DB_PASS', 'your-db-password')
  )
end

client = connect_db
result = client.query('SELECT 1')
puts result.first
client.close
```

### 4{{STEP_LETTER}}.5 Next Steps and Recommendations

{{SPECIFIC_RECOMMENDATIONS}}

Common recommendations:
- Store credentials in Secret Manager (not environment variables)
- Use IAM database authentication where possible
- Implement connection pooling for production workloads
- Set up monitoring and alerting for connection issues
- Enable SSL/TLS for connections over public networks
- Configure appropriate timeout and retry logic

---

## Completion

Display:
```
✅ {{RESOURCE_TYPE}} → Cloud SQL connection setup complete!

Summary:
- Cloud SQL Instance: [CLOUDSQL_INSTANCE_NAME]
- {{RESOURCE_TYPE}}: [{{PRIMARY_RESOURCE_VAR}}]
- Connection Method: [{{CONNECTION_METHOD}}]
- Connection String: {{CONNECTION_HOST}}:{{CONNECTION_PORT}}

{{COMPLETION_DETAILS}}

Next steps:
1. Store credentials securely (Secret Manager recommended)
2. Test connection from your application
3. Set up monitoring and alerting
4. Review security best practices
```

---

## TEMPLATE USAGE INSTRUCTIONS

This template file serves as a blueprint for creating new compute destination modules. Follow these instructions to customize it for a new compute type.

### Step 1: Identify Your Placeholders

Replace all `{{PLACEHOLDER}}` values with appropriate content for your compute type. Here's a comprehensive list:

#### Header Section Placeholders
- `{{COMPUTE_TYPE}}` - Name of compute type (e.g., "Cloud Functions", "App Engine", "Compute Engine VM")
- `{{COMPUTE_DESCRIPTION}}` - Brief description (e.g., "a Cloud Functions service", "an App Engine application")

#### Step Numbering
- `{{STEP_LETTER}}` - Letter suffix for steps (e.g., "E" for Step 2E, 3E, 4E)
  - Existing: A=GCE-VM, B=LOCAL-IDE, C=GKE, D=CLOUD-RUN
  - Use next available letter for new compute types

#### Step 2 - Resource Selection
- `{{RESOURCE_SELECTION_TITLE}}` - Title for resource selection (e.g., "Fetch and Select Cloud Functions")
- `{{LOADING_MESSAGE}}` - Loading message (e.g., "Fetching Cloud Functions... please wait")
- `{{RESOURCE_TYPE}}` - Singular resource name (e.g., "Function", "App")
- `{{RESOURCE_TYPE_PLURAL}}` - Plural resource name (e.g., "Functions", "Apps")
- `{{GCLOUD_LIST_COMMAND}}` - Command to list resources (e.g., `gcloud functions list --format="table(...)"`)
- `{{PRIMARY_RESOURCE_VAR}}` - Main variable name (e.g., `FUNCTION_NAME`, `APP_NAME`)
- `{{PRIMARY_RESOURCE_DESCRIPTION}}` - Description of primary variable
- `{{SECONDARY_RESOURCE_VAR}}` - Secondary variable (e.g., region, zone)
- `{{SECONDARY_RESOURCE_DESCRIPTION}}` - Description of secondary variable
- `{{ADDITIONAL_VARIABLES}}` - Any extra variables needed (can be empty)
- `{{CONFIRMATION_DETAILS}}` - Details shown in confirmation (e.g., "in region [REGION]")
- `{{ADDITIONAL_CONFIRMATION_LINES}}` - Extra confirmation lines (can be empty)

#### Step 3 - Network Validation
- `{{NETWORK_VALIDATION_TITLE}}` - Title for network validation section
- `{{GCLOUD_DESCRIBE_COMMAND}}` - Command to get resource details
- `{{RESOURCE_SPECIFIC_VARIABLES}}` - List of variables to extract (formatted as bullet points)
- `{{NETWORK_ANALYSIS_HEADER}}` - Header for analysis card (e.g., "GKE NETWORK ANALYSIS")
- `{{RESOURCE_SPECIFIC_CHECKS}}` - Additional rows in the analysis table (formatted as table rows)
- `{{CONNECTION_METHOD_OPTIONS}}` - Possible connection methods (e.g., "Private IP / Public IP / Proxy")
- `{{DECISION_TREE_LOGIC}}` - Specific logic for your compute type's connectivity decisions
- `{{RESOURCE_SPECIFIC_REMEDIATION}}` - Additional remediation commands specific to this resource type

#### Step 4 - Connection Testing and Code
- `{{CONNECTION_TESTING_TITLE}}` - Title for connection testing section
- `{{CONNECTION_METHOD}}` - Primary connection method (e.g., "Private IP", "Auth Proxy", "Unix Socket")
- `{{CONNECTION_HOST}}` - Host to connect to (can be placeholder or actual value)
- `{{CONNECTION_PORT}}` - Port to connect to (or description)
- `{{ADDITIONAL_CONNECTION_DETAILS}}` - Extra connection details (can be empty)
- `{{CONNECTIVITY_TEST_COMMANDS}}` - Description of how to test connectivity
- `{{TEST_COMMAND_POSTGRES}}` - PostgreSQL test command
- `{{TEST_COMMAND_MYSQL}}` - MySQL test command
- `{{TEST_COMMAND_SQLSERVER}}` - SQL Server test command
- `{{SPECIFIC_RECOMMENDATIONS}}` - Recommendations specific to this compute type
- `{{COMPLETION_DETAILS}}` - Additional completion details

### Step 2: Customize Decision Trees

The decision tree in Step 3 should reflect your compute type's networking capabilities:

**Example for VM-based compute:**
```
If Private IP available AND same VPC:
  → Direct Private IP connection
If different VPC:
  → VPC Peering or Cloud SQL Auth Proxy
If only Public IP:
  → Cloud SQL Auth Proxy or Authorized Networks
```

**Example for serverless compute:**
```
If Built-in Cloud SQL integration available:
  → Use native integration (Unix socket)
If VPC Connector configured:
  → Private IP via VPC Connector
Otherwise:
  → Cloud SQL Connector library
```

### Step 3: Add Code Examples

The template includes base code snippets. Customize the `{{CONNECTION_HOST}}` and `{{CONNECTION_PORT}}` placeholders:

- For **Private IP**: Use the actual private IP variable
- For **Auth Proxy**: Use `127.0.0.1` with appropriate port
- For **Unix Socket** (Cloud Run): Use `/cloudsql/{{CLOUDSQL_CONNECTION_NAME}}`
- For **Connector Libraries**: Include library-specific setup

### Step 4: Update GEMINI.md Routing Table

After creating your new compute module file, add it to the routing table in GEMINI.md:

```markdown
### Step 1.5: Select Connection Source (Compute Destination)

**User prompt:**
```
Where will you connect from?
1. GCE VM (Compute Engine)
2. Local IDE / Laptop
3. GKE (Kubernetes)
4. Cloud Run
5. {{NEW_COMPUTE_TYPE}}  ← Add your new option

Enter choice (1-5):
```

**Routing logic:**
- Choice 1 → Continue to compute/GCE-VM.md (Step 2A)
- Choice 2 → Continue to compute/LOCAL-IDE.md (Step 2B)
- Choice 3 → Continue to compute/GKE.md (Step 2C)
- Choice 4 → Continue to compute/CLOUD-RUN.md (Step 2D)
- Choice 5 → Continue to compute/{{NEW_FILE}}.md (Step 2{{STEP_LETTER}})  ← Add routing
```

### Step 5: Test Your Module

Before finalizing, verify:

1. All `{{PLACEHOLDERS}}` are replaced with actual values
2. Step numbering is consistent (2{{STEP_LETTER}}, 3{{STEP_LETTER}}, 4{{STEP_LETTER}})
3. Variable names are unique and descriptive
4. gcloud commands are syntactically correct
5. Code snippets use correct connection parameters
6. Decision tree logic matches your compute type's capabilities
7. References to components/NETWORK-VALIDATION.md and components/CODE-SNIPPETS.md are appropriate

### Common Compute Types to Consider

**Serverless:**
- Cloud Functions (Gen 1 & 2)
- App Engine (Standard & Flexible)
- Cloud Run Jobs

**Containers:**
- GKE Autopilot clusters
- Cloud Composer environments

**Specialized:**
- Cloud SQL Proxy on a bastion host
- Dataflow pipelines
- Vertex AI Workbench notebooks

### Best Practices

1. **Keep consistency** with existing modules (GCE-VM, LOCAL-IDE, GKE, CLOUD-RUN)
2. **Use descriptive variable names** that clearly indicate their purpose
3. **Provide complete gcloud commands** that users can copy-paste
4. **Include error handling** in decision trees for common failure scenarios
5. **Reference shared components** rather than duplicating content
6. **Test all commands** before finalizing the module
7. **Document prerequisites** clearly at the top of the file
8. **Use ASCII tables** for visual consistency in network analysis output
9. **Provide multiple language examples** (minimum: Python, Node.js, Java, Go)
10. **Include production recommendations** specific to your compute type

### Getting Help

- Review existing modules in `/compute/` for examples
- Check `/components/` for shared logic you can reference
- Refer to GCP documentation for gcloud command syntax
- Test with actual GCP resources before deploying to production
