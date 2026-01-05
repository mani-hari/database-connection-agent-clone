#!/usr/bin/env python3
"""
Phase 1: Automated Instruction Validator
Tests structural integrity of Gemini extension instruction files
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import json

@dataclass
class ValidationIssue:
    severity: str  # 'error', 'warning', 'info'
    file: str
    section: str
    message: str
    line: int = 0

class InstructionValidator:
    def __init__(self, md_file: str):
        self.file_path = Path(md_file)
        self.content = self.file_path.read_text()
        self.lines = self.content.split('\n')
        self.issues: List[ValidationIssue] = []
        self.stats = {
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'checks_passed': 0,
            'checks_total': 0
        }

    def add_issue(self, severity: str, section: str, message: str, line: int = 0):
        self.issues.append(ValidationIssue(severity, self.file_path.name, section, message, line))
        self.stats[f"{severity}s"] += 1

    def check_variable_format(self):
        """Check all variables use {VARIABLE} format, not VARIABLE or [VARIABLE]"""
        section = "Variable Format"
        self.stats['checks_total'] += 1

        # Find old-style UPPERCASE variables in commands (not in comments)
        bash_blocks = re.findall(r'```bash\n(.*?)```', self.content, re.DOTALL)
        old_vars = []
        for block in bash_blocks:
            # Look for bare UPPERCASE words that aren't common commands
            matches = re.findall(r'\b([A-Z][A-Z_]{2,})\b', block)
            for match in matches:
                # Exclude common commands and env vars
                if match not in ['PROJECT_ID', 'YOUR_DB', 'YOUR_USER', 'YOUR_PASSWORD', 'GKE_METADATA', 'VPC_NAME', 'EOF']:
                    if not re.search(rf'{{{match}}}', block):  # Not in {VAR} format
                        old_vars.append(match)

        if old_vars:
            unique_vars = list(set(old_vars))[:5]  # Show first 5
            self.add_issue('warning', section,
                          f"Found potential old-style variables (not in {{}} format): {', '.join(unique_vars)}")

        # Check for new {VARIABLE} format exists
        new_vars = re.findall(r'\{([A-Z_]+)\}', self.content)
        if new_vars:
            self.stats['checks_passed'] += 1
        else:
            self.add_issue('error', section, "No new-style {VARIABLE} format found")

    def check_ascii_tables(self):
        """Verify ASCII tables are well-formed"""
        section = "ASCII Tables"
        self.stats['checks_total'] += 1

        # Find tables with box-drawing characters
        tables = re.findall(r'(╔═+╗.*?╚═+╝)', self.content, re.DOTALL)

        if not tables:
            self.add_issue('warning', section, "No ASCII tables found (expected at least one)")
            return

        for i, table in enumerate(tables):
            # Check if table has proper structure
            if '║' not in table or '╠' not in table:
                self.add_issue('error', section, f"Table {i+1} is malformed (missing row separators)")
            else:
                self.stats['checks_passed'] += 1

    def check_gcloud_commands(self):
        """Validate gcloud command structure"""
        section = "gcloud Commands"
        self.stats['checks_total'] += 1

        gcloud_cmds = re.findall(r'gcloud ([^\n]+)', self.content)
        issues_found = False

        for cmd in gcloud_cmds:
            # Check describe commands have --format flag
            if 'describe' in cmd and '--format' not in cmd:
                self.add_issue('error', section,
                              f"Missing --format flag: gcloud {cmd[:50]}...")
                issues_found = True

            # Check list commands have --format flag
            if 'list' in cmd and '--format' not in cmd and 'extensions list' not in cmd:
                self.add_issue('warning', section,
                              f"List command without --format: gcloud {cmd[:50]}...")
                issues_found = True

        if not issues_found and gcloud_cmds:
            self.stats['checks_passed'] += 1

    def check_step_structure(self):
        """Verify step numbering is consistent"""
        section = "Step Structure"
        self.stats['checks_total'] += 1

        # Extract step numbers
        steps = re.findall(r'## Step (\w+):', self.content)

        # Determine expected pattern based on file
        if 'GCE-VM' in self.file_path.name:
            expected = ['2A', '3A', '4A']
        elif 'LOCAL-IDE' in self.file_path.name:
            expected = ['2B', '3B', '4B']
        elif 'GKE' in self.file_path.name:
            expected = ['2C', '3C', '4C']
        elif 'CLOUD-RUN' in self.file_path.name:
            expected = ['2D', '3D', '4D']
        else:
            self.stats['checks_passed'] += 1
            return

        if steps == expected:
            self.stats['checks_passed'] += 1
        else:
            self.add_issue('error', section,
                          f"Expected steps {expected}, found {steps}")

    def check_code_quality(self):
        """Check code snippets use best practices"""
        section = "Code Quality"
        self.stats['checks_total'] += 1

        # Find Python code blocks
        python_blocks = re.findall(r'```python\n(.*?)```', self.content, re.DOTALL)
        issues_found = False

        for block in python_blocks:
            # Check if code uses environment variables
            if 'your-db-user' in block or 'your-db-password' in block:
                if 'os.environ' not in block and 'process.env' not in block:
                    self.add_issue('warning', section,
                                  "Code snippet should use os.environ.get() for credentials")
                    issues_found = True

        if not issues_found:
            self.stats['checks_passed'] += 1

    def check_component_references(self):
        """Check if Component References section exists"""
        section = "Component References"
        self.stats['checks_total'] += 1

        if '**Component References:**' in self.content:
            # Check if all expected references are present
            required_refs = ['UI-CARDS.md', 'CODE-SNIPPETS.md', 'NETWORK-VALIDATION.md', 'REMEDIATION.md']
            missing = [ref for ref in required_refs if ref not in self.content]

            if missing:
                self.add_issue('warning', section, f"Missing component references: {', '.join(missing)}")
            else:
                self.stats['checks_passed'] += 1
        else:
            self.add_issue('error', section, "Component References section not found")

    def check_prerequisites(self):
        """Check if Prerequisites section exists"""
        section = "Prerequisites"
        self.stats['checks_total'] += 1

        if '**Prerequisites:**' in self.content:
            self.stats['checks_passed'] += 1
        else:
            self.add_issue('error', section, "Prerequisites section not found")

    def run_all_checks(self):
        """Run all validation checks"""
        print(f"\n🔍 Validating {self.file_path.name}...")

        self.check_prerequisites()
        self.check_component_references()
        self.check_variable_format()
        self.check_ascii_tables()
        self.check_gcloud_commands()
        self.check_step_structure()
        self.check_code_quality()

        return self.issues, self.stats


def generate_html_report(results: Dict):
    """Generate HTML report from validation results"""

    total_errors = sum(r['stats']['errors'] for r in results.values())
    total_warnings = sum(r['stats']['warnings'] for r in results.values())
    total_passed = sum(r['stats']['checks_passed'] for r in results.values())
    total_checks = sum(r['stats']['checks_total'] for r in results.values())

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Gemini Extension - Phase 1 Validation Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
        .pass {{ color: #10b981; }}
        .fail {{ color: #ef4444; }}
        .warn {{ color: #f59e0b; }}
        .file-section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .file-section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .issue {{
            padding: 12px;
            margin: 10px 0;
            border-left: 4px solid;
            border-radius: 4px;
        }}
        .issue.error {{
            background: #fee2e2;
            border-color: #ef4444;
        }}
        .issue.warning {{
            background: #fef3c7;
            border-color: #f59e0b;
        }}
        .issue.info {{
            background: #dbeafe;
            border-color: #3b82f6;
        }}
        .issue-header {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .no-issues {{
            color: #10b981;
            font-weight: bold;
            padding: 20px;
            text-align: center;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .summary-table th, .summary-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        .summary-table th {{
            background: #f9fafb;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 Phase 1: Instruction Validation Report</h1>
        <p>Automated structural validation of Gemini CLI extension instructions</p>
        <p><strong>Generated:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-label">Checks Passed</div>
            <div class="stat-value pass">✓ {total_passed}/{total_checks}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Errors Found</div>
            <div class="stat-value fail">✗ {total_errors}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Warnings</div>
            <div class="stat-value warn">⚠ {total_warnings}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Pass Rate</div>
            <div class="stat-value" style="color: {'#10b981' if total_passed/total_checks > 0.8 else '#f59e0b'}">
                {int(total_passed/total_checks*100)}%
            </div>
        </div>
    </div>
"""

    # File-by-file results
    for filename, data in results.items():
        issues = data['issues']
        stats = data['stats']

        html += f"""
    <div class="file-section">
        <h2>📄 {filename}</h2>
        <table class="summary-table">
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Checks Passed</td>
                <td class="pass">✓ {stats['checks_passed']}/{stats['checks_total']}</td>
            </tr>
            <tr>
                <td>Errors</td>
                <td class="fail">{stats['errors']}</td>
            </tr>
            <tr>
                <td>Warnings</td>
                <td class="warn">{stats['warnings']}</td>
            </tr>
        </table>
"""

        if issues:
            for issue in issues:
                html += f"""
        <div class="issue {issue.severity}">
            <div class="issue-header">{issue.severity.upper()}: {issue.section}</div>
            <div>{issue.message}</div>
        </div>
"""
        else:
            html += '<div class="no-issues">✅ No issues found!</div>'

        html += "</div>\n"

    html += """
</body>
</html>
"""

    return html


if __name__ == '__main__':
    # Files to validate
    compute_files = [
        'compute/GCE-VM.md',
        'compute/LOCAL-IDE.md',
        'compute/GKE.md',
        'compute/CLOUD-RUN.md'
    ]

    results = {}

    print("=" * 60)
    print("🚀 PHASE 1: AUTOMATED INSTRUCTION VALIDATION")
    print("=" * 60)

    for file in compute_files:
        validator = InstructionValidator(file)
        issues, stats = validator.run_all_checks()
        results[file] = {'issues': issues, 'stats': stats}

    # Generate HTML report
    html_report = generate_html_report(results)
    report_path = Path('test_validation_report.html')
    report_path.write_text(html_report)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    total_errors = sum(r['stats']['errors'] for r in results.values())
    total_warnings = sum(r['stats']['warnings'] for r in results.values())
    total_passed = sum(r['stats']['checks_passed'] for r in results.values())
    total_checks = sum(r['stats']['checks_total'] for r in results.values())

    print(f"\n✓ Checks Passed: {total_passed}/{total_checks}")
    print(f"✗ Errors: {total_errors}")
    print(f"⚠ Warnings: {total_warnings}")
    print(f"📈 Pass Rate: {int(total_passed/total_checks*100)}%")

    print(f"\n📄 Full report: {report_path.absolute()}")

    # Print critical issues
    if total_errors > 0:
        print("\n❌ CRITICAL ISSUES:")
        for file, data in results.items():
            for issue in data['issues']:
                if issue.severity == 'error':
                    print(f"  • {file}: {issue.section} - {issue.message}")

    print("\n" + "=" * 60)
    print("✅ Phase 1 validation complete!")
    print("=" * 60)
