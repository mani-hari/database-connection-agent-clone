# Cloud SQL Easy Connect - Gemini CLI Extension

A Gemini CLI extension that guides and automates the steps to connect a Cloud SQL instance to a compute destination such as GCE VMs, GKE, Cloud Run etc. It authenticates, lists resources, validates networking, and (with your approval) runs the necessary `gcloud` commands for you.

## Quick Start (Google Cloud Shell)
Follow these steps in Cloud Shell to register and use the extension.

1. **Verify Gemini CLI exists (install if missing):**
   ```bash
   gemini --version || gcloud components install gemini
   ```
2. **Install the extension from this repo (registers the tool):**
   ```bash
   gemini extensions install https://github.com/mani-hari/database-connection-agent-clone
   ```
3. **Confirm it registered correctly:**
   ```bash
   gemini extensions list | grep database-connect-assist
   ```
4. **Run Gemini CLI with the extension enabled:**
   ```bash
   gemini --extensions database-connect-assist
   ```
5. **Start the guided flow:**
   ```
   Help me connect my GCE VM to Cloud SQL
   ```

## Uninstall
```bash
gemini extensions uninstall database-connect-assist
```

## What the Extension Does (Step-by-Step)
**Easy to use UI in Terminal 'To Do list':** The extensions presents everything in an easy to consume Planning card UI. You start with a concise, fully expanded to-do list that shows every step, marks current/complete items, and resurfaces it as you move through each task. Use Ctrl+T to toggle open states. 

- **Step 1:** Authenticate and enumerate Cloud SQL instances in your active project; you pick one by number or name.
- **Step 2:** Ask where the app is hosted (GCE VM, Laptop/IDE, Compute Engine managed service, GKE, Cloud Run, Other). The GCE VM path is fully implemented: the tool shows a loader while listing VMs alphabetically and lets you choose by number or name.
- **Step 3:** Validate network compatibility (private vs public IP, VPC alignment, PSA/PSC where applicable). It recommends private IP, proposes remediations, and runs `gcloud`/API updates after you consent.
- **Step 4:** Test connectivity and emit language-specific connection snippets tailored to the chosen connectivity method.

## Troubleshooting
If something fails during the guided flow, see `docs/troubleshooting.md` for a quick checklist that covers authentication, IP configuration, VPC alignment, firewall rules, and Cloud SQL Auth Proxy health.

## Notes
- The agent runs commands for you once you approve a change—no need to copy/paste `gcloud` yourself.
- Prompts stay concise and always show the connection to-do list—fully expanded and forced open—when transitioning between steps. The primary guidance in each step (e.g., network analysis results) is highlighted in a callout/boxed style so it stands out.
- Extension metadata lives in `gemini-extension.json` (name: `database-connect-assist`, version: `2.0.0`).



## Files
- `gemini-extension.json` - Extension manifest
- `GEMINI.md` - Detailed behavior/instructions the AI follows
