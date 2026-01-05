# ASCII UI Component Library

This document defines reusable ASCII UI templates for the Gemini CLI agent instruction set. These components ensure consistent visual formatting across all compute environment files.

---

## Component Index

1. [NETWORK_ANALYSIS_CARD](#network_analysis_card)
2. [PROGRESS_TRACKER](#progress_tracker)
3. [SELECTION_MENU](#selection_menu)
4. [CONNECTION_SUMMARY](#connection_summary)
5. [STATUS_INDICATORS](#status_indicators)
6. [LOADING_MESSAGE](#loading_message)

---

## NETWORK_ANALYSIS_CARD

**Purpose:** Display network validation results in a structured table format.

**Box Characters:**
- Double-line outer box: `╔ ═ ╗ ║ ╠ ╣ ╚ ╝`
- Single-line dividers: `─ │ ┼`

### Template

```
╔══════════════════════════════════════════════════════════════════╗
║                    {{TITLE}}                                      ║
╠══════════════════════════════════════════════════════════════════╣
║ {{RESOURCE_1_LABEL}}: {{RESOURCE_1_VALUE}}                        ║
║ {{RESOURCE_2_LABEL}}: {{RESOURCE_2_VALUE}}                        ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ {{CHECK_1_NAME}}               │ {{✅/❌}} │ {{CHECK_1_DETAILS}}   ║
║ {{CHECK_2_NAME}}               │ {{✅/❌}} │ {{CHECK_2_DETAILS}}   ║
║ {{CHECK_3_NAME}}               │ {{✅/❌}} │ {{CHECK_3_DETAILS}}   ║
║ {{CHECK_4_NAME}}               │ {{✅/❌}} │ {{CHECK_4_DETAILS}}   ║
╠══════════════════════════════════════════════════════════════════╣
║ {{RECOMMENDATION_LINE}}                                           ║
╚══════════════════════════════════════════════════════════════════╝
```

### Variables

- `{{TITLE}}` - Card header title (e.g., "NETWORK ANALYSIS RESULTS")
- `{{RESOURCE_1_LABEL}}` / `{{RESOURCE_1_VALUE}}` - First resource identifier (e.g., "Cloud SQL Instance: my-db")
- `{{RESOURCE_2_LABEL}}` / `{{RESOURCE_2_VALUE}}` - Second resource identifier (e.g., "GCE VM: my-vm")
- `{{CHECK_N_NAME}}` - Name of the validation check (left-aligned, max ~30 chars)
- `{{✅/❌}}` - Status indicator (success/failure)
- `{{CHECK_N_DETAILS}}` - Additional details about the check result
- `{{RECOMMENDATION_LINE}}` - Bottom recommendation text

### Example Usage

```
╔══════════════════════════════════════════════════════════════════╗
║                    NETWORK ANALYSIS RESULTS                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Cloud SQL Instance: my-postgres-db                                ║
║ GCE VM: web-server-1                                              ║
╠══════════════════════════════════════════════════════════════════╣
║ CHECK                          │ STATUS   │ DETAILS               ║
╠────────────────────────────────┼──────────┼───────────────────────╣
║ Cloud SQL Private IP           │ ✅       │ 10.0.1.5              ║
║ Cloud SQL Public IP            │ ✅       │ 35.1.2.3              ║
║ VM Internal IP                 │ ✅       │ 10.0.1.10             ║
║ VM External IP                 │ ❌       │ None                  ║
║ Same VPC Network               │ ✅       │ default               ║
║ Private Services Access        │ ✅       │ Enabled               ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED CONNECTION METHOD: Private IP                         ║
╚══════════════════════════════════════════════════════════════════╝
```

### Alternative: Connection Options Card

For displaying multiple connection options:

```
╔══════════════════════════════════════════════════════════════════╗
║                    {{TITLE}}                                      ║
╠══════════════════════════════════════════════════════════════════╣
║ {{RESOURCE_LABEL}}: {{RESOURCE_VALUE}}                            ║
║ {{CONNECTION_LABEL}}: {{CONNECTION_VALUE}}                        ║
╠══════════════════════════════════════════════════════════════════╣
║ OPTION │ METHOD                    │ BEST FOR                    ║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   1    │ {{METHOD_1}}              │ {{USE_CASE_1}}              ║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   2    │ {{METHOD_2}}              │ {{USE_CASE_2}}              ║
╠────────┼───────────────────────────┼─────────────────────────────╣
║   3    │ {{METHOD_3}}              │ {{USE_CASE_3}}              ║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED: {{RECOMMENDATION}}                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## PROGRESS_TRACKER

**Purpose:** Show step completion status and planning confirmation.

### Template (Single Item)

```
✅ {{ITEM_DESCRIPTION}}
```

### Template (Multiple Items)

```
✅ {{COMPLETED_ITEM_1}}
✅ {{COMPLETED_ITEM_2}}
▶️ {{IN_PROGRESS_ITEM}}
○ {{PENDING_ITEM_1}}
○ {{PENDING_ITEM_2}}
```

### Variables

- `{{COMPLETED_ITEM}}` - Item that has been completed (prefix with ✅)
- `{{IN_PROGRESS_ITEM}}` - Item currently being worked on (prefix with ▶️)
- `{{PENDING_ITEM}}` - Item not yet started (prefix with ○)
- `{{ITEM_DESCRIPTION}}` - Clear description of the item/step

### Example Usage

**Single confirmation:**
```
✅ Selected VM: web-server-1 in zone us-central1-a
```

**Multi-item progress:**
```
✅ Authentication configured
✅ Cloud SQL instance selected
✅ GCE VM selected
▶️ Network validation in progress
○ Connection testing
○ Code deployment
```

**Step completion summary:**
```
✅ Application Default Credentials: Configured
✅ Cloud SQL Admin API: Enabled
✅ IAM Permissions: cloudsql.client granted
```

---

## SELECTION_MENU

**Purpose:** Present numbered options for user selection.

### Template (Basic List)

```
{{PROMPT_TEXT}}
1. {{OPTION_1}}
2. {{OPTION_2}}
3. {{OPTION_3}}
4. {{OPTION_4}}

{{SELECTION_INSTRUCTION}}
```

### Template (With Categories)

```
{{SECTION_TITLE}}
{{DIVIDER}}

{{PROMPT_TEXT}}
1. {{OPTION_1}}
2. {{OPTION_2}}
3. {{OPTION_3}}

Enter choice (1-{{MAX_NUMBER}}):
```

### Variables

- `{{PROMPT_TEXT}}` - Question or instruction above the list
- `{{OPTION_N}}` - Description of each selectable option
- `{{SELECTION_INSTRUCTION}}` - How to make the selection (e.g., "Enter choice (1-6):")
- `{{SECTION_TITLE}}` - Optional header for the menu section
- `{{DIVIDER}}` - Optional divider (e.g., "─────────────────────────────────")
- `{{MAX_NUMBER}}` - Highest option number

### Example Usage

**Language selection:**
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

**Binary choice:**
```
Do you want to:
1. Connect an existing Cloud Run service to Cloud SQL
2. Set up connection for a new Cloud Run service (not yet deployed)

Enter choice (1-2):
```

**Resource selection with table header:**
```
Select a Cloud SQL instance:
─────────────────────────────────────────────────
NAME                    REGION         DATABASE
─────────────────────────────────────────────────
1. my-postgres-db       us-central1    POSTGRES_15
2. prod-mysql-db        us-west1       MYSQL_8_0
3. test-sqlserver-db    us-east1       SQLSERVER_2019

Enter selection (number or name):
```

---

## CONNECTION_SUMMARY

**Purpose:** Display final connection configuration details in a simple, readable format.

### Template

```
{{TITLE}}
{{DIVIDER}}
{{KEY_1}}: {{VALUE_1}}
{{KEY_2}}: {{VALUE_2}}
{{KEY_3}}: {{VALUE_3}}
{{KEY_4}}: {{VALUE_4}}
{{DIVIDER}}
```

### Variables

- `{{TITLE}}` - Summary title (e.g., "CONNECTION SUMMARY", "PRODUCTION RECOMMENDATIONS")
- `{{DIVIDER}}` - Text divider using dashes (typically "─────────────────────────────────")
- `{{KEY_N}}` - Configuration key/label (e.g., "Method", "Host", "Port")
- `{{VALUE_N}}` - Corresponding value

### Example Usage

**Basic connection details:**
```
CONNECTION SUMMARY
─────────────────────────────────
Method: Cloud SQL Auth Proxy
Host: 127.0.0.1
Port: 5432
Proxy Connection: my-project:us-central1:my-db
─────────────────────────────────
```

**Cloud Run summary:**
```
CONNECTION SUMMARY
─────────────────────────────────
Cloud Run Service: my-api-service
Cloud SQL Instance: project:region:my-db
Connection Method: Built-in Unix Socket
─────────────────────────────────
```

**GKE summary:**
```
CONNECTION SUMMARY
─────────────────────────────────
Method: Cloud SQL Auth Proxy Sidecar
Cloud SQL Instance: project:region:instance
GKE Cluster: production-cluster
Namespace: default
Workload Identity: Enabled
Service Account: cloudsql-sa
─────────────────────────────────
```

**Production recommendations (multi-section):**
```
PRODUCTION RECOMMENDATIONS
─────────────────────────────────
1. Use Secret Manager for credentials (not env vars)

2. Connection Pooling:
   - Cloud Run scales to zero - connections close
   - Use Cloud SQL Connector for automatic reconnection
   - Set appropriate pool_recycle (1800 seconds)

3. Cold Start Optimization:
   - Keep min-instances=1 if latency matters
   - Use connection pooling libraries

4. Monitoring:
   - Enable Cloud SQL insights
   - Set up alerts for connection errors
   - Monitor Cloud Run metrics
─────────────────────────────────
```

---

## STATUS_INDICATORS

**Purpose:** Standardize symbols used throughout the interface to indicate status, progress, and outcomes.

### Symbol Reference

| Symbol | Meaning | Usage Context |
|--------|---------|---------------|
| ✅ | Success, Enabled, Completed, Yes | Successful checks, enabled features, completed steps |
| ❌ | Failure, Disabled, Error, No | Failed checks, disabled features, missing requirements |
| ▶️ | In Progress, Current Step | Currently executing step or active item |
| ○ | Pending, Not Started, Todo | Steps not yet started, queued items |
| → | Prompt, User Action Required | Indicates user should respond or take action |

### Usage Guidelines

1. **Status checks (in tables):**
   - Use `✅` or `❌` in the STATUS column
   - Always provide context in the DETAILS column

2. **Progress tracking:**
   - Use `✅` for completed steps
   - Use `▶️` for the current/active step
   - Use `○` for pending/future steps

3. **User prompts:**
   - Prefix with `→` to indicate action required
   - Example: `→ Ask: "Ready to proceed to Step 3? (yes/no)"`

4. **Confirmations:**
   - Use `✅` prefix for positive confirmations
   - Example: `✅ Auth Proxy installed`

### Example Usage

**In network analysis table:**
```
║ Cloud SQL Admin API            │ ✅       │ Enabled               ║
║ Application Default Creds      │ ❌       │ Not configured        ║
```

**In step progression:**
```
✅ Step 1: Authentication - Completed
✅ Step 2: Resource Selection - Completed
▶️ Step 3: Network Validation - In Progress
○ Step 4: Connection Testing - Pending
○ Step 5: Code Deployment - Pending
```

**In confirmations:**
```
✅ Cloud SQL Admin API: Enabled
✅ Application Default Credentials: Configured
```

**In user prompts:**
```
→ Ask: "Ready to proceed to Step 4 (Connection Testing)? (yes/no)"
```

---

## LOADING_MESSAGE

**Purpose:** Display progress indicators while fetching or processing data.

### Template

```
{{ACTION_DESCRIPTION}}... please wait
```

### Variables

- `{{ACTION_DESCRIPTION}}` - Brief description of the action being performed (present participle form)

### Example Usage

```
Fetching GCE instances... please wait
```

```
Fetching GKE clusters... please wait
```

```
Fetching Cloud Run services... please wait
```

```
Validating network configuration... please wait
```

```
Testing database connection... please wait
```

```
Deploying Cloud SQL Auth Proxy... please wait
```

### Guidelines

- Always use present participle form (verb + "ing")
- Keep message concise and actionable
- End with "... please wait"
- Display before executing long-running commands
- Follow with result indicators (✅/❌) after completion

---

## Design Guidelines

### Character Sets

**Double-line box (primary containers):**
```
╔ ═ ╗
║   ║
╠ ═ ╣
║   ║
╚ ═ ╝
```

**Single-line dividers (internal sections):**
```
─ │ ┼
```

**Text dividers (simple summaries):**
```
─────────────────────────────────
```

### Box Width Standard

- Standard width: 66 characters (inner content)
- Full width with borders: 68 characters
- This ensures readability across most terminal sizes

### Alignment

- **Left-align:** Resource names, check names, labels
- **Center-align:** Titles, headers
- **Right-align:** Rarely used, only for numeric data when appropriate

### Spacing

- Use spaces for padding within table cells
- Maintain consistent column widths within the same table
- Leave one space after `║` before content starts
- Leave one space before `║` at line end

### Color and Formatting

This component library defines structure only. Actual terminal coloring should be applied by the rendering system:

- **Titles:** Bold
- **✅ symbols:** Green
- **❌ symbols:** Red
- **▶️ symbols:** Yellow/Amber
- **○ symbols:** Gray/Dim
- **Borders:** Default or subtle gray

---

## Implementation Notes

### Variable Substitution

When implementing these templates:

1. Replace `{{VARIABLE_NAME}}` with actual values
2. Pad values to maintain alignment in tables
3. Truncate long values with "..." if they exceed column width
4. For dynamic lists (like checks), repeat the row template as needed

### Responsive Considerations

For narrow terminals (<80 characters):
- Use CONNECTION_SUMMARY instead of NETWORK_ANALYSIS_CARD when possible
- Stack information vertically rather than in tables
- Simplify option text in SELECTION_MENU

### Accessibility

- All status is conveyed through both symbols (✅/❌) and text ("Enabled"/"Disabled")
- Never rely on symbols alone for critical information
- Use clear, descriptive text in DETAILS columns

---

## Version History

- **v1.0** (2025-12-21): Initial component library based on compute environment files
