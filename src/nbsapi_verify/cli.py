import glob
import json
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import click
import pytest
import yaml

from .formatting import ResultCapture, format_json, format_results, render_html


class TestType(str, Enum):
    ALL = "all"
    AUTH = "auth"
    PUBLIC = "public"


class NoAliasDumper(yaml.SafeDumper):
    """Custom YAML dumper that prevents creation of aliases for duplicate values."""

    def ignore_aliases(self, data):
        return True


def save_yaml(data: dict, file_path: Path) -> None:
    """Save data to YAML file without aliases."""
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, Dumper=NoAliasDumper)


def get_config_locations() -> list[Path]:
    """Get the possible locations for common.yaml in priority order."""
    return [
        Path.cwd() / "common.yaml",  # Current directory
        Path(click.get_app_dir("nbsinfra_verify")) / "common.yaml",  # User config dir
    ]


def find_config() -> Optional[Path]:
    """Find existing config file in priority order."""
    for path in get_config_locations():
        if path.exists():
            return path
    return None


def get_config_path(config_dir: Optional[str] = None) -> Path:
    """Get the path where config should be written/read.

    Args:
        config_dir: Optional custom config directory path. If provided,
                   this overrides the default locations.

    """
    if config_dir:
        path = Path(config_dir) / "common.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # Default to current directory for new configs
    return Path.cwd() / "common.yaml"


@click.command()
@click.option(
    "--generate", is_flag=True, help="Generate common.yaml configuration file"
)
@click.option(
    "--config-dir",
    type=str,
    help="Custom directory for common.yaml (defaults to current directory)",
)
@click.option("--host", type=str, help="API host (e.g., http://localhost:8000)")
@click.option(
    "--testid",
    type=int,
    default=1,
    help="Existing test user ID (defaults to 1)",
)
@click.option("--username", type=str, help="Existing test username for auth tests")
@click.option("--password", type=str, help="Existing test password for auth tests")
@click.option(
    "--solution",
    type=int,
    default=1,
    help="Existing test solution ID (defaults to 1)",
)
@click.option(
    "--project",
    type=int,
    default=1,
    help="Existing test project ID (defaults to 1)",
)
@click.option(
    "--impact",
    type=int,
    default=1,
    help="Existing test impact ID (defaults to 1)",
)
@click.option(
    "--measure",
    type=int,
    default=1,
    help="Existing test measure ID (defaults to 1)",
)
@click.option(
    "--test-type",
    type=click.Choice(["all", "auth", "public"]),
    default="all",
    help="Type of tests to run",
)
@click.option(
    "--json-output",
    type=click.Path(),
    default=None,
    is_flag=True,
    flag_value="",
    help="Output test results as JSON",
)
@click.option(
    "--html-output",
    type=click.Path(),
    default=None,
    is_flag=True,
    flag_value="",
    help="Output test results as HTML",
)
def cli(
    generate: bool,
    config_dir: Optional[str],
    host: Optional[str],
    testid: int,
    username: Optional[str],
    password: Optional[str],
    solution: int,
    project: int,
    impact: int,
    measure: int,
    test_type: str,
    json_output: Optional[str],
    html_output: Optional[str],
):
    """NbSAPI test runner and configuration generator."""
    if generate:
        if not host:
            click.echo("Error: --host is required when using --generate", err=True)
            sys.exit(1)

        config_path = get_config_path(config_dir)  # Write to explicit path or cwd

        # Create common config
        config = {"variables": {"host": host}}
        config["variables"].update({"user_id": testid})
        config["variables"].update({"solution_id": solution})
        config["variables"].update({"project_id": project})
        config["variables"].update({"impact_id": impact})
        config["variables"].update({"measure_id": measure})

        if username and password:
            config["variables"].update({"username": username, "password": password})

        # Write common config
        save_yaml(config, config_path)
        click.echo(f"Generated configuration file at: {config_path}")
        return

    # Running tests
    config_path = None
    if config_dir:
        # If explicit config dir provided, only look there
        config_path = Path(config_dir) / "common.yaml"
        if not config_path.exists():
            click.echo(
                f"Error: Configuration file not found at {config_path}",
                err=True,
            )
            sys.exit(1)
    else:
        # Otherwise search in priority order
        config_path = find_config()
        if not config_path:
            locations = "\n  ".join(str(p) for p in get_config_locations())
            click.echo(
                "Error: Configuration file not found in any of these locations:\n  "
                + locations
                + "\n\nPlease run with --generate flag first to create configuration.",
                err=True,
            )
            sys.exit(1)

    # Load config to check available test types
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Check for test type mismatch
    has_auth_config = "username" in config.get(
        "variables", {}
    ) and "password" in config.get("variables", {})

    # Detect test type mismatch
    if test_type in (TestType.AUTH, TestType.ALL) and not has_auth_config:
        click.echo(
            f"Error: Test type '{test_type}' requested but auth configuration is missing.\n"
            "Auth tests require 'username' and 'password' in the configuration.\n"
            "Please regenerate the configuration with --username and --password parameters.",
            err=True,
        )
        sys.exit(1)

    # Get the package's test directory
    package_dir = Path(__file__).parent
    test_dir = package_dir / "tests"

    if not test_dir.exists():
        click.echo(f"Error: Test directory not found at {test_dir}", err=True)
        sys.exit(1)

    # Verify that requested test types have matching test files

    # Get all test files and check for their markers
    test_files = glob.glob(str(test_dir / "*.tavern.yaml"))

    # Check if there are any test files with requested markers
    has_auth_tests = False
    has_public_tests = False

    for test_file in test_files:
        with open(test_file) as f:
            content = f.read()
            if "marks:\n- auth" in content:
                has_auth_tests = True
            if "marks:\n- public" in content:
                has_public_tests = True

    # Verify requested test type has matching test files
    if test_type == TestType.AUTH and not has_auth_tests:
        click.echo(
            f"Error: Test type '{test_type}' requested but no auth test files found.\n"
            "Make sure auth test files are generated and properly marked.",
            err=True,
        )
        sys.exit(1)

    if test_type == TestType.PUBLIC and not has_public_tests:
        click.echo(
            f"Error: Test type '{test_type}' requested but no public test files found.\n"
            "Make sure public test files are generated and properly marked.",
            err=True,
        )
        sys.exit(1)

    if test_type == TestType.ALL and not (has_auth_tests and has_public_tests):
        missing = []
        if not has_auth_tests:
            missing.append("auth")
        if not has_public_tests:
            missing.append("public")
        click.echo(
            f"Error: Test type '{test_type}' requested but some test types are missing: {', '.join(missing)}.\n"
            "Make sure all test types are generated before running 'all' tests.",
            err=True,
        )
        sys.exit(1)

    # Prepare pytest arguments
    pytest_args = [
        str(test_dir),
        "-q",  # Quiet mode
        "--tb=no",  # Disable traceback
        "--no-header",  # Remove header
        "--no-summary",  # Remove summary
        f"--tavern-global-cfg={config_path}",
    ]

    # Add test type marker if not 'all'
    if test_type != TestType.ALL:
        pytest_args.extend(["-m", test_type])

    # Create result capture
    capture = ResultCapture()

    # Set environment variable to allow project ID override for testing
    os.environ["ALLOW_PROJECT_ID_OVERRIDE"] = "true"

    # Run pytest with capture
    exit_code = pytest.main(pytest_args, plugins=[capture])

    # Print formatted results to terminal
    click.echo(format_results(capture))

    # Always show DELETE operations note
    delete_message = (
        f"\n{'=' * 60}\n"
        "ℹ️  NOTE: DELETE endpoint tests are intentionally excluded\n"  # noqa: RUF001
        f"{'=' * 60}\n"
        "DELETE operations are not included in conformance tests to prevent\n"
        "data destruction when running against production databases.\n"
        "\n"
        "If you need to test DELETE operations, please:\n"
        "1. Use an isolated test environment\n"
        "2. Create custom tests specifically for DELETE operations\n"
        "3. Ensure proper data cleanup and restoration procedures\n"
        f"{'=' * 60}"
    )
    click.echo(delete_message)

    # Handle JSON output if requested
    if json_output is not None:
        # Use config_dir if provided, otherwise use current directory
        base_dir = os.path.curdir if not config_dir else config_dir

        # If a path was explicitly provided, use it; otherwise use the default filename
        if json_output and json_output != "":
            json_path = json_output
        else:
            json_path = os.path.join(base_dir, "nbsapi_verify_report.json")

        json_data = format_json(capture)
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=2)
        click.echo(f"JSON report saved to: {json_path}")

    # Handle HTML output if requested
    if html_output is not None:
        # Use config_dir if provided, otherwise use current directory
        base_dir = os.path.curdir if not config_dir else config_dir

        # If a path was explicitly provided, use it; otherwise use the default filename
        if html_output and html_output != "":
            html_path = html_output
        else:
            html_path = os.path.join(base_dir, "nbsapi_verify_report.html")

        # Generate HTML using JSON data as input
        json_data = format_json(capture) if not json_output else None
        html_content = render_html(capture, json_data)
        with open(html_path, "w") as f:
            f.write(html_content)
        click.echo(f"HTML report saved to: {html_path}")

    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
