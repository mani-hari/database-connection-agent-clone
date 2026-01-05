#!/bin/bash
# Quick script to list Cloud SQL instances and VMs

echo "================================"
echo "CLOUD SQL INSTANCES"
echo "================================"
gcloud sql instances list --project=firestore-fs --format="table(name,databaseVersion,region,state)"

echo ""
echo "================================"
echo "COMPUTE VMs"
echo "================================"
gcloud compute instances list --project=firestore-fs --format="table(name,zone,status)"

echo ""
echo "================================"
echo "INSTRUCTIONS"
echo "================================"
echo "Use the 'name' column values (not connection names) in test_live_e2e.py"
echo ""
echo "Example:"
echo "  Instance name: mani-postgres-01  (USE THIS)"
echo "  Connection name: firestore-fs:us-central1:mani-postgres-01  (NOT THIS)"
