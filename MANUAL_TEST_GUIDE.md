# Phase 2: Manual Testing Guide

This guide provides step-by-step instructions to manually test the Gemini CLI extension instructions in your GCP Cloud Shell.

## Prerequisites

- Access to GCP Cloud Shell in project `firestore-fs`
- Infrastructure already provisioned:
  - Cloud SQL instances: `mani-postgres-01`, `mani-postgres-customvpc`
  - VMs: `mani-vm-test01`, `mani-vm-test02`

## Option 1: Automated Testing (Recommended)

Run the automated test script in Cloud Shell:

```bash
# Clone the repository
git clone https://github.com/mani-hari/database-connection-agent-clone.git
cd database-connection-agent-clone

# Run Phase 2 automated tests
python3 test_live_e2e.py

# View the report
cat test_live_e2e_report.html
```

The script will:
- Test both scenarios (happy path and edge case)
- Validate all gcloud commands from GCE-VM.md
- Generate HTML report with pass/fail results

---

## Option 2: Manual Step-by-Step Testing

If you prefer to test manually, follow these scenarios:

### Scenario 1: Happy Path (Same VPC - Default Network)

**Resources:**
- Cloud SQL: `mani-postgres-01`
- VM: `mani-vm-test01` (us-central1-a)
- Expected: Both in default VPC, private IP connection should work

#### Step 0: Set Project

```bash
gcloud config set project firestore-fs
```

#### Step 1: Cloud SQL Selection

```bash
# List instances
gcloud sql instances list --format="table(name,databaseVersion,region,state)"
```

**✅ Expected:** See `mani-postgres-01` in the list

```bash
# Describe selected instance
gcloud sql instances describe mani-postgres-01 --format="yaml(name,databaseVersion,region)"
```

**✅ Expected:** Instance details returned (POSTGRES_*, us-central1, RUNNABLE)

#### Step 2A: GCE VM Selection

```bash
# List VMs
gcloud compute instances list --format="table(name,zone,machineType.basename(),status)" --sort-by=name
```

**✅ Expected:** See `mani-vm-test01` in the list

#### Step 3A: Network Validation

```bash
# Get Cloud SQL network details
gcloud sql instances describe mani-postgres-01 --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,region)"
```

**✅ Expected output to capture:**
- `CLOUDSQL_PRIVATE_IP` (from ipAddresses where type=PRIVATE)
- `CLOUDSQL_PUBLIC_IP` (from ipAddresses where type=PRIMARY)
- `CLOUDSQL_VPC` (from settings.ipConfiguration.privateNetwork)
- `CLOUDSQL_CONNECTION_NAME` (from connectionName field)

**Record values here:**
- Private IP: _______________
- Public IP: _______________
- VPC: _______________
- Connection Name: _______________

```bash
# Get VM network details
gcloud compute instances describe mani-vm-test01 --zone=us-central1-a --format="yaml(name,networkInterfaces[].network,networkInterfaces[].networkIP)"
```

**✅ Expected output to capture:**
- `VM_INTERNAL_IP` (from networkInterfaces[0].networkIP)
- `VM_VPC` (from networkInterfaces[0].network - extract VPC name from path)

**Record values here:**
- VM Internal IP: _______________
- VM VPC: _______________

**Manual Check:**
- [ ] Do Cloud SQL VPC and VM VPC match? (Should be YES for this scenario)
- [ ] Is Private IP configured for Cloud SQL? (Should be YES)

```bash
# Check Private Services Access
gcloud services vpc-peerings list --network=default --project=firestore-fs
```

**✅ Expected:** Should see `servicenetworking.googleapis.com` peering connection

#### Step 4A: Connection Testing

```bash
# Test PostgreSQL connectivity from VM (requires private IP from above)
gcloud compute ssh mani-vm-test01 --zone=us-central1-a --command="pg_isready -h <CLOUDSQL_PRIVATE_IP> -p 5432"
```

**✅ Expected:** Connection successful (if psql tools installed) OR "command not found" (which is fine - validates SSH works)

---

### Scenario 2: Edge Case (Different VPCs - Needs Remediation)

**Resources:**
- Cloud SQL: `mani-postgres-customvpc`
- VM: `mani-vm-test02` (us-central1-a)
- Expected: Different VPCs, should detect mismatch and suggest remediation

#### Step 1: Cloud SQL Selection

```bash
gcloud sql instances list --format="table(name,databaseVersion,region,state)"
```

**✅ Expected:** See `mani-postgres-customvpc` in the list

```bash
gcloud sql instances describe mani-postgres-customvpc --format="yaml(name,databaseVersion,region)"
```

**✅ Expected:** Instance details returned

#### Step 2A: VM Selection

```bash
gcloud compute instances list --format="table(name,zone,machineType.basename(),status)" --sort-by=name
```

**✅ Expected:** See `mani-vm-test02` in the list

#### Step 3A: Network Validation

```bash
# Get Cloud SQL network details
gcloud sql instances describe mani-postgres-customvpc --format="yaml(name,connectionName,ipAddresses,settings.ipConfiguration.privateNetwork,region)"
```

**Record values here:**
- Private IP: _______________
- VPC: _______________

```bash
# Get VM network details
gcloud compute instances describe mani-vm-test02 --zone=us-central1-a --format="yaml(name,networkInterfaces[].network,networkInterfaces[].networkIP)"
```

**Record values here:**
- VM Internal IP: _______________
- VM VPC: _______________

**Manual Check:**
- [ ] Do Cloud SQL VPC and VM VPC match? (Should be NO for this scenario - this is the edge case)
- [ ] Does the instruction detect the mismatch? (Should suggest remediation)

**Expected Remediation Suggestion:**
- Instructions should recommend VPC peering OR moving resources to same VPC
- Should display warning about VPC mismatch

---

## Test Results Template

Copy this template to record your results:

```markdown
## Phase 2 Test Results

**Tested by:** [Your name]
**Date:** [Date]
**Project:** firestore-fs

### Scenario 1: Happy Path (Same VPC)
- [ ] Step 1.2: Cloud SQL instance listed
- [ ] Step 1.4: Instance details retrieved
- [ ] Step 2A.2: VM listed
- [ ] Step 3A.1: Cloud SQL network details retrieved
- [ ] Step 3A.2: VM network details retrieved
- [ ] Step 3A.3: VPC match detected correctly
- [ ] Step 3A.4: Private Services Access verified
- [ ] Step 4A.2: Connection test command validated

**Overall Result:** PASS / FAIL
**Notes:**

### Scenario 2: Edge Case (Different VPCs)
- [ ] Step 1.2: Cloud SQL instance listed
- [ ] Step 1.4: Instance details retrieved
- [ ] Step 2A.2: VM listed
- [ ] Step 3A.1: Cloud SQL network details retrieved
- [ ] Step 3A.2: VM network details retrieved
- [ ] Step 3A.3: VPC mismatch detected correctly
- [ ] Step 3A.5: Remediation commands offered

**Overall Result:** PASS / FAIL
**Notes:**

### Issues Found
[List any issues, errors, or discrepancies]

### Suggestions
[Any improvements or corrections needed]
```

---

## Success Criteria

**Phase 2 is successful if:**

1. ✅ All gcloud commands execute without errors
2. ✅ Network validation correctly identifies VPC match/mismatch
3. ✅ Private IP connection is recommended when VPCs match
4. ✅ Remediation is offered when VPCs don't match
5. ✅ Connection test commands are syntactically correct
6. ✅ All variables are properly substituted with actual values

---

## Next Steps After Testing

1. Document any issues found in GitHub Issues
2. Update instruction files if commands need correction
3. Run Phase 1 validator again after any changes
4. Re-test affected scenarios

---

## Troubleshooting

**If gcloud commands fail:**
- Ensure you're in the correct project: `gcloud config get-value project`
- Check authentication: `gcloud auth list`
- Verify resources exist: `gcloud sql instances list` and `gcloud compute instances list`

**If VPCs don't match expectations:**
- Check actual VPC configuration in Console
- Update test scenarios in `test_live_e2e.py` if infrastructure changed

**If Private Services Access is missing:**
- Follow remediation steps in `compute/GCE-VM.md` section 3A.5
