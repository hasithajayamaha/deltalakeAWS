# deltalake-aws

Utilities for provisioning a lightweight AWS data lake footprint with boto3. The package exposes a Python API and CLI that ensure the core resources exist and are configured consistently.

## What it does

- Creates or updates an S3 bucket with recommended security defaults (versioning, encryption, public access block, tags) and core prefixes (raw/ curated/ analytics/).
- Creates or updates a Glue database for the analytics catalog and optionally a Glue crawler targeting the raw zone.
- Creates or updates an Athena workgroup that writes query results back into the lake, optionally encrypted with your KMS key.

## Installation

Create and activate a virtual environment, then install the project:

    python -m venv .venv
    source .venv/bin/activate
    pip install -e .

If you are using Python 3.10 or earlier, the dependency resolver will pull in "tomli" automatically for TOML parsing.

## Configuration

The CLI loads its settings from a TOML file with a [datalake] table. All fields map directly to the DataLakeConfig dataclass in datalake_aws.config.

    [datalake]
    region = "us-east-1"
    bucket_name = "my-company-data-lake"
    glue_database = "analytics_catalog"
    raw_prefix = "raw/"
    processed_prefix = "curated/"
    analytics_prefix = "analytics/"
    kms_key_id = "arn:aws:kms:us-east-1:123456789012:key/example"
    crawler_name = "raw-zone-crawler"
    crawler_role_arn = "arn:aws:iam::123456789012:role/GlueCrawlerRole"
    crawler_schedule = "cron(0 6 * * ? *)"
    athena_workgroup = "lakehouse-workgroup"

    [datalake.tags]
    Environment = "dev"
    Owner = "data-eng"

Only region, bucket_name, and glue_database are required. Provide crawler_* values only when you want a Glue crawler managed for you.

## Running the CLI

    python -m datalake_aws --region us-east-1 --config datalake.toml       --access-key YOUR_AWS_ACCESS_KEY_ID       --secret-key YOUR_AWS_SECRET_ACCESS_KEY

Credentials are optional. If you omit them, boto3 falls back to the standard AWS credential chain (environment variables, shared config/credentials files, instance metadata, etc.).

## Using the Python API

    from datalake_aws import AwsCredentials, DataLakeConfig, DataLakeDeployer, SessionFactory

    config = DataLakeConfig(
        region="us-east-1",
        bucket_name="my-company-data-lake",
        glue_database="analytics_catalog",
    )
    credentials = AwsCredentials(
        access_key_id="YOUR_AWS_ACCESS_KEY_ID",
        secret_access_key="YOUR_AWS_SECRET_ACCESS_KEY",
    )

    sessions = SessionFactory(region=config.region, credentials=credentials)
    deployer = DataLakeDeployer(sessions)
    deployer.deploy(config)

The deployer methods are idempotent; subsequent runs keep resources in sync.

## Testing changes locally

The project has no runtime dependencies beyond boto3 and tomli (for Python < 3.11). You can quickly validate the code compiles by running:

    python -m compileall src

For integration testing you will need AWS credentials with permissions for S3, Glue, Athena, and optionally KMS.
