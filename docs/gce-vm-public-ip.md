# Cloud SQL Connection: GCE VM via Public IP

This instruction set guides connecting a Google Compute Engine VM to Cloud SQL using Public IP connectivity with Cloud SQL Auth Proxy (recommended) or Authorized Networks.

---

## ⚠️ Security Notice

Public IP connections expose your database to the internet. We strongly recommend:
1. **Use Cloud SQL Auth Proxy** (automatic encryption + IAM authentication)
2. **Or** configure strict Authorized Networks
3. **Consider** switching to Private IP if possible

---

## Prerequisites Check

```bash
# Verify authentication
gcloud auth list

# Verify current project
gcloud config get-value project

# Required permissions: roles/cloudsql.client, roles/compute.viewer
```

---

## STEP 1: Gather Information

### 1.1 Get Cloud SQL Instance Details

```bash
# List Cloud SQL instances
gcloud sql instances list --format="table(name,databaseVersion,region,ipAddresses)"

# User prompt: "Which Cloud SQL instance do you want to connect to?"
# Store as: CLOUD_SQL_INSTANCE

# Get instance details
gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="json(name,connectionName,ipAddresses,region,settings.ipConfiguration)"
```

**Extract and store:**
- `CONNECTION_NAME`: project:region:instance format
- `PUBLIC_IP`: The public IP address (ipAddresses where type=PRIMARY)
- `REGION`: Instance region
- `DB_VERSION`: postgresql, mysql, or sqlserver

### 1.2 Verify Public IP is Enabled

```bash
# Check if public IP is enabled
PUBLIC_IP=$(gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="value(ipAddresses[0].ipAddress)")

if [ -z "$PUBLIC_IP" ]; then
    echo "❌ Public IP is not enabled on this instance"
    echo "Enable it with: gcloud sql instances patch ${CLOUD_SQL_INSTANCE} --assign-ip"
else
    echo "✅ Public IP: ${PUBLIC_IP}"
fi
```

### 1.3 Get GCE VM Details

```bash
# List all VMs
gcloud compute instances list --format="table(name,zone,networkInterfaces[0].accessConfigs[0].natIP,status)"

# User prompt: "Which GCE VM do you want to connect from?"
# Store as: VM_NAME, VM_ZONE

# Get VM's external IP
VM_EXTERNAL_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "VM External IP: ${VM_EXTERNAL_IP}"
```

---

## STEP 2: Choose Connection Method

### Option A: Cloud SQL Auth Proxy (RECOMMENDED)

✅ **Benefits:**
- Automatic SSL/TLS encryption
- IAM-based authentication
- No need to manage SSL certificates
- No need to whitelist IP addresses
- Works with dynamic IPs

### Option B: Authorized Networks (Direct Connection)

⚠️ **Considerations:**
- Requires whitelisting VM's external IP
- VM needs static external IP (or update whitelist when IP changes)
- Must manage SSL certificates manually
- Less secure than Auth Proxy

---

## STEP 2A: Cloud SQL Auth Proxy Method (Recommended)

### 2A.1 SSH into the GCE VM

```bash
gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE}
```

### 2A.2 Install Cloud SQL Auth Proxy

```bash
# Download the Cloud SQL Auth Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.19.0/cloud-sql-proxy.linux.amd64

# Make it executable
chmod +x cloud-sql-proxy

# Move to a system path (optional)
sudo mv cloud-sql-proxy /usr/local/bin/
```

### 2A.3 Verify VM Service Account Permissions

```bash
# Check VM's service account
gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="value(serviceAccounts[0].email)"

# The service account needs roles/cloudsql.client role
# If using default compute service account, grant the role:
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL=$(gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="value(serviceAccounts[0].email)")

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client"
```

### 2A.4 Start the Auth Proxy

```bash
# Start proxy in background (listens on localhost:5432 for PostgreSQL)
# PostgreSQL:
cloud-sql-proxy --port 5432 ${CONNECTION_NAME} &

# MySQL:
cloud-sql-proxy --port 3306 ${CONNECTION_NAME} &

# SQL Server:
cloud-sql-proxy --port 1433 ${CONNECTION_NAME} &

# Verify it's running
ps aux | grep cloud-sql-proxy
```

### 2A.5 Test Connection via Auth Proxy

**For PostgreSQL:**
```bash
# Install client if needed
sudo apt-get update && sudo apt-get install -y postgresql-client

# Connect via localhost (proxy forwards to Cloud SQL)
psql "host=127.0.0.1 port=5432 dbname=${DB_NAME} user=${DB_USER}"
# Enter password when prompted

# Test query
SELECT version();
\q
```

**For MySQL:**
```bash
# Install client if needed
sudo apt-get update && sudo apt-get install -y mysql-client

# Connect via localhost
mysql -h 127.0.0.1 -u ${DB_USER} -p ${DB_NAME}

# Test query
SELECT VERSION();
exit
```

---

## STEP 2B: Authorized Networks Method

### 2B.1 Get VM's External IP

```bash
# Ensure VM has a static external IP (recommended)
VM_EXTERNAL_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${VM_ZONE} --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "VM External IP to whitelist: ${VM_EXTERNAL_IP}"
```

### 2B.2 Add VM IP to Authorized Networks

```bash
# Add the VM's IP to Cloud SQL authorized networks
gcloud sql instances patch ${CLOUD_SQL_INSTANCE} \
    --authorized-networks=${VM_EXTERNAL_IP}/32 \
    --quiet

# Note: This replaces existing authorized networks
# To append, first get existing networks:
EXISTING=$(gcloud sql instances describe ${CLOUD_SQL_INSTANCE} --format="value(settings.ipConfiguration.authorizedNetworks[].value)" | tr '\n' ',')
gcloud sql instances patch ${CLOUD_SQL_INSTANCE} \
    --authorized-networks="${EXISTING}${VM_EXTERNAL_IP}/32"
```

### 2B.3 Get SSL Certificates (Recommended)

```bash
# Create client certificate
gcloud sql ssl client-certs create ${VM_NAME}-cert client-key.pem \
    --instance=${CLOUD_SQL_INSTANCE}

# Download server CA cert
gcloud sql instances describe ${CLOUD_SQL_INSTANCE} \
    --format="value(serverCaCert.cert)" > server-ca.pem

# Get the client certificate
gcloud sql ssl client-certs describe ${VM_NAME}-cert \
    --instance=${CLOUD_SQL_INSTANCE} \
    --format="value(cert)" > client-cert.pem
```

### 2B.4 SSH and Test Direct Connection

```bash
# SSH into VM
gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE}

# Copy certificates to VM (run from local machine)
# gcloud compute scp server-ca.pem client-cert.pem client-key.pem ${VM_NAME}:~/ --zone=${VM_ZONE}
```

**For PostgreSQL:**
```bash
# Install client
sudo apt-get update && sudo apt-get install -y postgresql-client

# Connect with SSL
psql "host=${PUBLIC_IP} port=5432 dbname=${DB_NAME} user=${DB_USER} sslmode=verify-ca sslrootcert=server-ca.pem sslcert=client-cert.pem sslkey=client-key.pem"
```

**For MySQL:**
```bash
# Install client
sudo apt-get update && sudo apt-get install -y mysql-client

# Connect with SSL
mysql -h ${PUBLIC_IP} -u ${DB_USER} -p ${DB_NAME} \
    --ssl-ca=server-ca.pem \
    --ssl-cert=client-cert.pem \
    --ssl-key=client-key.pem
```

---

## STEP 3: Network Validation Summary

### For Auth Proxy Method:
- ✅ VM has outbound internet access (port 443)
- ✅ VM service account has `roles/cloudsql.client`
- ✅ Cloud SQL API enabled in project
- ✅ Auth Proxy running and listening

### For Authorized Networks Method:
- ✅ VM external IP is whitelisted
- ✅ VM has static IP (recommended)
- ✅ SSL certificates configured
- ✅ Firewall allows outbound to Cloud SQL port

---

## STEP 4: Generate Application Code

### Ask Programming Language

```
What programming language is your application written in?
1. Python
2. Node.js
3. Java
4. Go
5. PHP
```

### Python with Auth Proxy

**Install dependencies:**
```bash
pip install pg8000 sqlalchemy cloud-sql-python-connector
```

**Connection code (using connector - handles proxy internally):**
```python
import sqlalchemy
from google.cloud.sql.connector import Connector

connector = Connector()

def getconn():
    conn = connector.connect(
        "${CONNECTION_NAME}",
        "pg8000",
        user="${DB_USER}",
        password="${DB_PASSWORD}",
        db="${DB_NAME}",
        ip_type="PUBLIC"  # Uses public IP through connector
    )
    return conn

engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

# Test connection
with engine.connect() as connection:
    result = connection.execute(sqlalchemy.text("SELECT 1"))
    print(result.fetchone())

connector.close()
```

**Connection code (connecting through local Auth Proxy):**
```python
import psycopg2

# Auth Proxy is running locally on port 5432
conn = psycopg2.connect(
    host="127.0.0.1",  # Localhost - proxy forwards to Cloud SQL
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

### Node.js with Auth Proxy

**Install dependencies:**
```bash
npm install pg @google-cloud/cloud-sql-connector
```

**Connection code:**
```javascript
const { Connector } = require('@google-cloud/cloud-sql-connector');
const { Pool } = require('pg');

async function connect() {
    const connector = new Connector();

    const clientOpts = await connector.getOptions({
        instanceConnectionName: '${CONNECTION_NAME}',
        ipType: 'PUBLIC',
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

### Java with Auth Proxy

**Maven dependency:**
```xml
<dependency>
    <groupId>com.google.cloud.sql</groupId>
    <artifactId>postgres-socket-factory</artifactId>
    <version>1.15.0</version>
</dependency>
```

**Connection code:**
```java
String jdbcUrl = String.format(
    "jdbc:postgresql:///${DB_NAME}?" +
    "cloudSqlInstance=${CONNECTION_NAME}&" +
    "socketFactory=com.google.cloud.sql.postgres.SocketFactory&" +
    "ipTypes=PUBLIC&" +
    "user=${DB_USER}&" +
    "password=${DB_PASSWORD}"
);

Connection conn = DriverManager.getConnection(jdbcUrl);
```

---

## STEP 5: Running Auth Proxy as a Service (Production)

### Create systemd service:

```bash
sudo tee /etc/systemd/system/cloud-sql-proxy.service << EOF
[Unit]
Description=Cloud SQL Auth Proxy
After=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
ExecStart=/usr/local/bin/cloud-sql-proxy --port 5432 ${CONNECTION_NAME}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable cloud-sql-proxy
sudo systemctl start cloud-sql-proxy

# Check status
sudo systemctl status cloud-sql-proxy
```

---

## STEP 6: Security Best Practices

✅ **Use Auth Proxy** - Handles encryption and authentication automatically
✅ **Use IAM authentication** - No passwords to manage
✅ **Store secrets in Secret Manager** - Never hardcode credentials
✅ **Use static IPs** - If using Authorized Networks, prevent lockouts
✅ **Consider Private IP** - More secure than public, better performance
✅ **Enable audit logging** - Track database access

---

## Troubleshooting

### Auth Proxy won't start:
```bash
# Check logs
journalctl -u cloud-sql-proxy -f

# Verify service account permissions
gcloud projects get-iam-policy $(gcloud config get-value project) \
    --filter="bindings.members:serviceAccount:${SA_EMAIL}"
```

### Connection refused:
```bash
# Verify proxy is running
netstat -tlnp | grep 5432

# Check if Cloud SQL is accessible
curl -v https://sqladmin.googleapis.com/
```

### Authorized Networks - Connection timeout:
```bash
# Verify IP is whitelisted
gcloud sql instances describe ${CLOUD_SQL_INSTANCE} \
    --format="value(settings.ipConfiguration.authorizedNetworks[])"

# Check your current external IP matches
curl ifconfig.me
```

---

## Success!

🎉 Your GCE VM is now connected to Cloud SQL via Public IP!

**Summary:**
- Cloud SQL Instance: `${CLOUD_SQL_INSTANCE}`
- Connection Name: `${CONNECTION_NAME}`
- Public IP: `${PUBLIC_IP}`
- GCE VM: `${VM_NAME}`
- Connection Method: Auth Proxy (Secure) / Authorized Networks
