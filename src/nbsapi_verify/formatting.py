import datetime as dt
import os
import re
from datetime import datetime
from typing import Any, Optional

from _pytest.reports import TestReport
from jinja2 import Template


class ResultCapture:
    def __init__(self):
        self.passed: list[str] = []
        self.failed: list[dict[str, str]] = []
        self.skipped: list[str] = []
        self.total_duration: float = 0.0
        self.start_time: datetime = datetime.now(tz=dt.timezone.utc)

    def pytest_runtest_logreport(self, report: TestReport):
        if report.when == "call":  # Only process the test result, not setup/teardown
            test_id = report.nodeid

            # Extract endpoint from test_id
            # Format is typically: path/to/test_name_endpoint.tavern.yaml::test_name
            # We want to extract the endpoint part (/contact, /v1/api/users, etc.)

            endpoint_match = re.search(r"test_.+?_(.+?)\.tavern\.yaml", test_id)
            if endpoint_match:
                # Replace underscores with slashes to reconstruct the API endpoint
                endpoint = endpoint_match.group(1).replace("_", "/")
                # Add leading slash for clarity
                endpoint = f"/{endpoint}"
            else:
                # Fallback to original test_id if pattern not found
                endpoint = test_id

            if report.passed:
                self.passed.append(endpoint)
            elif report.failed:
                self.failed.append(
                    {
                        "id": endpoint,
                        "error": str(report.longrepr)
                        if report.longrepr
                        else "No error details available",
                    }
                )
            elif report.skipped:
                self.skipped.append(endpoint)

            if hasattr(report, "duration"):
                self.total_duration += report.duration


def format_results(capture: ResultCapture) -> str:
    """Format test results into a nice string, following common test output conventions."""
    output = []
    failures = False

    # Summary line
    _ = len(capture.passed) + len(capture.failed) + len(capture.skipped)
    output.append(f"\nNbSAPI Conformance Test Summary ({capture.total_duration:.1f}s)")
    output.append("=" * 40)

    # Short summary counts
    summary_parts = []
    if capture.passed:
        summary_parts.append(f"{len(capture.passed)} passed")
    if capture.failed:
        summary_parts.append(f"{len(capture.failed)} failed")
    if capture.skipped:
        summary_parts.append(f"{len(capture.skipped)} skipped ⏭️")
    output.append(", ".join(summary_parts))

    # Only show detailed output for failures
    if capture.failed:
        failures = True
        output.append("\nFailures")
        output.append("-" * 40)
        for test in capture.failed:
            output.append(f"❌ {test['id']}")
            # Format error message with proper indentation
            error_lines = test["error"].split("\n")
            output.extend(f"    {line}" for line in error_lines)
            output.append("")  # Empty line between failures

    # If there were skips, list them briefly
    if capture.skipped:
        output.append("\nSkipped Tests")
        output.append("-" * 40)
        output.extend(f"⏭️  {test}" for test in capture.skipped)
    if not failures:
        output.append(
            "\n✨ Congratulations, your NbSAPI implementation is conformant! ✨"
        )

    return "\n".join(output)


def format_json(capture: ResultCapture) -> dict[str, Any]:
    """Format test results as a JSON-serializable dictionary."""
    total = len(capture.passed) + len(capture.failed) + len(capture.skipped)

    return {
        "summary": {
            "total": total,
            "passed": len(capture.passed),
            "failed": len(capture.failed),
            "skipped": len(capture.skipped),
            "duration": round(capture.total_duration, 1),
            "timestamp": capture.start_time.strftime("%l:%M%p %Z on %b %d, %Y"),
        },
        "tests": {
            "passed": [test_id for test_id in capture.passed],
            "failed": capture.failed,
            "skipped": [test_id for test_id in capture.skipped],
        },
        "is_conformant": len(capture.failed) == 0,
        "delete_note": {
            "title": "DELETE endpoint tests are intentionally excluded",
            "message": "DELETE operations are not included in conformance tests to prevent data destruction when running against production databases.",
            "recommendations": [
                "Use an isolated test environment",
                "Create custom tests specifically for DELETE operations",
                "Ensure proper data cleanup and restoration procedures",
            ],
        },
    }


def render_html(
    capture: ResultCapture, json_data: Optional[dict[str, Any]] = None
) -> str:
    """Render test results as HTML using a Jinja2 template."""

    # Use the JSON data if provided, otherwise generate it
    data = json_data if json_data is not None else format_json(capture)

    # Get the HTML template
    template_path = os.path.join(os.path.dirname(__file__), "templates", "report.html")

    with open(template_path) as f:
        template_content = f.read()

    # Render the template
    template = Template(template_content)
    return template.render(data=data)
