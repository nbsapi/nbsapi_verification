# NbSAPI Verification Tool

`nbsapi_verify` is a standalone tool designed to verify that your API implementation conforms to the <https://nbsapi.org> OpenAPI specification, currently at version 2.0.0

## Installation and Usage
### Installation (temporary)
#### Using [pipx](https://pipx.pypa.io)
`pipx nbsapi_verify --help`

#### Using [uvx](https://docs.astral.sh/uv/guides/tools/)
`uvx nbsapi_verify --help`

### Installation (permanent, on `$PATH`)
If you would prefer the tool to be **installed** on your `PATH` you can run:

`pipx install nbsapi_verify` or `uv tool install nbsapi_verify`. You can then run `nbsapi_verify` without prefixes.

### Installation as a _package_
You can also install the package using your preferred Python package manager:

#### Using pip
```shell
pip install nbsapi_verify
```

#### Using uv
```shell
uv add nbsapi_verify
```

#### Using poetry
```shell
poetry add nbsapi_verify
```

After installation, you can run the tool using the installed script:
```shell
nbsapi_verify --help
```

### Usage
`nbsapi_verify` requires a small amount of configuration:

1. First, generate a verification config. This requires you to specify:
    - the host the API is running on
    - a valid username
    - the password for that username
    - the ID of that user
    - a path for the verification config to be stored (optional: it defaults to the current working directory)
    - the test type to be run: `all`, `auth`, `user`: the `auth` tests will exercise the write API functions, while the `user` tests will exercise the read API functions (defaults to `all`).

In order to test your API while locally developing, that command might look like:

```shell
nbsapi_verify --generate \
    --host http://localhost:8000 \
    --test-type all \
    --username testuser \
    --password testpass \
    --project 1 \
    --solution 1\
    --impact 1 \
    --measure 1 \
    --config-dir ~
```

If the command completes sucessfully, you can run the verification tool:

```shell
nbsapi_verify --config-dir ~
```

You can also generate JSON and HTML reports of the test results:

```shell
# Generate default JSON report (nbsapi_verify_report.json)
nbsapi_verify --config-dir ~ --json-output

# Generate default HTML report (nbsapi_verify_report.html)
nbsapi_verify --config-dir ~ --html-output

# Generate both reports
nbsapi_verify --config-dir ~ --json-output --html-output
```

When all tests pass, your API implementation is conformant to the `NbsAPI` specification!


# Conformance Test Data Requirements

This document describes the test data requirements for running API conformance tests against the NBS API.

## Overview

The conformance tests validate that the API implementation matches the OpenAPI specification. However, since these tests may run against production databases where data creation/deletion is not appropriate, they rely on existing test data.

## Required Test Data

For all conformance tests to pass, the following data must exist in the database:

### Projects
- **Project ID: `1`** - Must exist for project-related endpoint tests
  - Required for: GET, PATCH, DELETE `/v2/api/projects/1`
  - Required for: GET `/v2/api/projects/1/export`
  - Required for: GET `/v2/api/projects/1/export/deltares`
  - Required for: POST/DELETE `/v2/api/projects/1/solutions/1`

### Solutions (Nature-Based Solutions)
- **Solution ID: `1`** - Must exist for solution-related tests
  - Required for: GET, PATCH `/v2/api/solutions/solutions/1`
  - Required for: GET `/v2/api/solutions/solutions/1/geojson`
  - Required for: project-solution relationship tests

### Impacts
- **Impact ID: `1`** - Must exist for impact tests
  - Required for: GET `/v2/api/impacts/impacts/1`
  - Required for: GET `/v2/api/impacts/solutions/1/impacts`

### Measure Types
- **Measure ID: `1`** - Must exist for measure type tests
  - Required for: GET, PATCH `/v2/measure_types/1`
  - Note: DELETE tests are intentionally excluded from conformance tests

### Users
- **Username: `testuser`** with **Password: `testpass`** - Required for authenticated endpoints
  - Used for obtaining JWT tokens for protected endpoints

## Configuration

The test runner accepts these IDs as configuration options:

```bash
# Generate configuration with test data IDs
nbsapi-verify --generate \
    --host http://localhost:8000 \
    --username testuser \
    --password testpass \
    --project 1 \
    --solution 1 \
    --impact 1 \
    --measure 1
```

**Important**: The conformance tests use the `project_id` query parameter to create projects with predictable IDs for subsequent tests to reference. No special server configuration is required.

## Database Setup

### Development/Testing Environment

For development environments, you can create the required test data:

```sql
-- Create test user (adjust based on your auth system)
INSERT INTO users (username, password_hash) VALUES ('testuser', '<hashed_password>');

-- Create test measure type
INSERT INTO measure_types (id, name, description) VALUES ('1', 'Test Measure', 'Test measure type');

-- Create test solution
INSERT INTO naturebasedsolution (id, name, definition, measure_id) VALUES 
(1, 'Test Solution', 'Test nature-based solution', '1');

-- Create test project
INSERT INTO projects (id, title, description) VALUES 
('1', 'Test Project', 'Test project for conformance tests');

-- Create test impact
INSERT INTO impacts (id, magnitude, solution_id) VALUES 
(1, 100.0, 1);
```

### Production Environment

For production environments:
1. Identify existing data that can serve as test subjects
2. Update the configuration to use those IDs
3. Ensure the test user has appropriate permissions but limited scope

## Excluded Tests

The following types of tests are intentionally excluded from conformance testing:

### DELETE Operations
DELETE endpoints are skipped because:
- They permanently destroy data
- Running against production databases would be destructive
- They create dependencies between test execution order

Excluded DELETE endpoints:
- `DELETE /v2/measure_types/{measure_id}`
- `DELETE /v2/api/projects/{project_id}`
- `DELETE /v2/api/projects/{project_id}/solutions/{solution_id}`

### Data Creation Tests
Tests that create new data may fail in production environments due to:
- Unique constraints (if test data already exists)
- Permission restrictions
- Database triggers or validation rules

## Test Failure Analysis

### 404 Errors (Data Not Found)
If you see 404 errors like "Project not found", "Solution not found":
- Verify the required test data exists in the database
- Check that the IDs in your configuration match existing data
- Ensure the test user has read access to the data

### 409 Conflicts (Data Already Exists)
If you see 409 errors for creation endpoints:
- This is normal behavior when test data already exists
- The tests expect either 200 (success) or 409 (conflict) responses
- No action needed unless you're getting different error codes

### Authentication Errors
If you see 401/403 errors:
- Verify the test user credentials are correct
- Check that the user has appropriate permissions
- Ensure the JWT token is being generated correctly

## Best Practices

1. **Use Dedicated Test Data**: Create specific test records rather than using production data
2. **Document Test IDs**: Keep track of which IDs are reserved for testing
3. **Isolate Test Data**: Use specific naming conventions (e.g., "Test Project") to identify test records
4. **Regular Cleanup**: In development environments, periodically clean up accumulated test data
5. **Monitor Production**: When running against production, monitor for any unintended side effects

## Troubleshooting

### Common Issues

1. **"Project not found" errors**: The most common issue is missing project ID 1
2. **Authentication failures**: Usually incorrect test user credentials
3. **Measure type conflicts**: Trying to create measure types with existing IDs

### Debugging Steps

1. Check database for required test data:
   ```sql
   SELECT id, title FROM projects WHERE id = '1';
   SELECT id, name FROM naturebasedsolution WHERE id = 1;
   SELECT id FROM impacts WHERE id = 1;
   SELECT id, name FROM measure_types WHERE id = '1';
   ```

2. Verify test user can authenticate:
   ```bash
   curl -X POST http://localhost:8000/auth/token \
     -d "username=testuser&password=testpass"
   ```

3. Test individual endpoints manually:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/v2/api/projects/1
   ```

## Updating Test Data Requirements

When adding new conformance tests, document any additional data requirements here. Consider:
- What IDs/entities the test requires
- Whether the test is destructive
- If it should be excluded from production testing
- What configuration options might be needed

## Help
`nbsapi_verify --help`
