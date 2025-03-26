# NbSAPI Verification Tool

`nbsapi_verify` is a standalone tool designed to verify that your API implementation conforms to the <https://nbsapi.org> OpenAPI specification, currently at Version 1.0.

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
    --test-type all
    --username testuser \
    --password testpass \
    --testid 1 \
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

## Help
`nbsapi_verify --help`
