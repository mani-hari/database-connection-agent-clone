# Cloud SQL Easy Connect - Troubleshooting Guide

Use this checklist when the guided flow reports failures or connectivity issues. The steps focus on quick validation commands the extension can run on your behalf and the remediations to apply.

---

## 1) Authentication & Project Context
- **Verify active account**: `gcloud auth list`
- **Refresh credentials**: `gcloud auth login` and `gcloud auth application-default login`
- **Confirm project**: `gcloud config get-value project`
- **Service account scope (on GCE)**: `gcloud compute instances describe VM_NAME --zone=ZONE --format="value(serviceAccounts[0].scopes)"`
- **Fix**: Re-authenticate, or attach a service account with the `roles/cloudsql.client` role.

## 2) Cloud SQL Configuration
- **Check private/public IP**: `gcloud sql instances describe INSTANCE --format="yaml(ipAddresses,settings.ipConfiguration)"`
- **Enable private IP** (preferred): `gcloud sql instances patch INSTANCE --network=projects/PROJECT/global/networks/VPC --no-assign-ip`
- **Enable public IP** (if required): `gcloud sql instances patch INSTANCE --assign-ip`
- **Fix**: Turn on the connectivity option that matches your compute network (private IP is recommended when available).

## 3) VM Network Details
- **List network + IPs**: `gcloud compute instances describe VM_NAME --zone=ZONE --format="yaml(networkInterfaces)"`
- **External IP present?**: Look for `accessConfigs[0].natIP`
- **Fix**: If using public IP connectivity, add an external IP; if using private IP, ensure the VM sits on the target VPC/subnet.

## 4) VPC Alignment & Private Service Access
- **Compare VPCs**: `gcloud compute instances describe VM_NAME --zone=ZONE --format="value(networkInterfaces[0].network)" | awk -F'/' '{print $NF}'`
  vs `gcloud sql instances describe INSTANCE --format="value(settings.ipConfiguration.privateNetwork)" | awk -F'/' '{print $NF}'`
- **Check PSA peering**: `gcloud services vpc-peerings list --network=VPC --project=PROJECT`
- **Fix**: Move the VM to the Cloud SQL VPC, set up VPC peering, or create the Private Service Access connection.

## 5) Firewall & Egress Rules
- **List rules on VPC**: `gcloud compute firewall-rules list --filter="network:VPC" --format="table(name,direction,allowed,denied,targetTags)"`
- **Look for denies**: Any `EGRESS` rules blocking ports 3306/5432/1433.
- **Fix**: Add an egress allow rule for the database port or remove conflicting deny rules.

## 6) Auth Proxy Health (Public or Private)
- **Check process**: `ps aux | grep cloud-sql-proxy`
- **Verify listening**: `ss -lntp | grep cloud-sql-proxy`
- **Restart**: `sudo systemctl restart cloud-sql-proxy` (if installed as a service) or restart the background job.
- **Fix**: Ensure the proxy uses the correct `CONNECTION_NAME` and port, and that the VM/service account has `roles/cloudsql.client`.

## 7) Database Credentials & Connectivity Tests
- **Test via psql/mysql/sqlcmd** using the IP/port surfaced by the chosen connectivity method.
- **IAM DB auth**: Confirm the instance database version supports it and that the user has `roles/cloudsql.instanceUser`.
- **Fix**: Reset passwords, confirm database user existence, and retry the connectivity test after proxy/network fixes.

---

### Quick Decision Tree
1. **Auth check clean?** If not, re-authenticate or fix service account roles.
2. **Instance IP availability?** Enable private IP (preferred) or public IP.
3. **VPC alignment?** Match VPCs or set up peering/PSA.
4. **Firewall clear?** Ensure no egress blocks on DB port.
5. **Proxy running?** Restart and retest.

If all checks pass and the connection still fails, collect command outputs above and escalate with the specific error message (SSL, auth, timeout, etc.).
