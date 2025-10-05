# deltalake-aws

Utilities for provisioning a lightweight AWS data lake footprint with boto3. The package exposes a Python API and CLI that ensure the core resources exist and are configured consistently.

## What it does

- Hardened S3 bucket with raw / processed / analytics prefixes.
- Glue database plus optional crawler for raw zone cataloguing.
- Athena workgroup pinned to the analytics zone for querying.
- Optional Kinesis Data Firehose stream and service role feeding the raw zone.
- Optional IAM role scaffolding for processing frameworks (Databricks, Glue, EMR).
- Optional Iceberg/Delta Glue table seed for ACID style workloads.
- Optional VPC endpoints for private access to S3, Glue, and Athena services.

## Key configuration knobs

- region / bucket_name / glue_database: core identifiers for the lake.
- firehose.*: stream_name, role_name, buffering controls, and prefix for Kinesis Data Firehose.
- processing_role: IAM assume-role policy plus managed/inline policies for your processing platform.
- table_format + transactional_table_name + enable_transactional_tables: control Iceberg or Delta scaffolding.
- athena_workgroup, kms_key_id, tags: tighten governance and encryption defaults.
- crawler_*: optional Glue crawler wiring when ingest discovery is needed.
- vpc_endpoints.*: configure VPC endpoints for private access to AWS services (S3, Glue, Athena).

See examples/datalake.toml for a basic configuration and examples/datalake-with-vpc.toml for a configuration with VPC endpoints.

## Running the CLI

Run: python -m datalake_aws --region YOUR_REGION --config path/to/config.toml [--access-key KEY --secret-key SECRET]. The deployer reports each resource with a created/updated/skipped status for observability.

## Using the Python API

Initialise DataLakeConfig (optionally injecting FirehoseConfig, IamRoleConfig, and VpcEndpointConfig), build a SessionFactory, then call DataLakeDeployer.deploy(config) to converge resources in AWS.

Example with VPC endpoints:
```python
from datalake_aws import DataLakeConfig, VpcEndpointConfig, SessionFactory, DataLakeDeployer

vpc_config = VpcEndpointConfig(
    vpc_id="vpc-0123456789abcdef0",
    subnet_ids=["subnet-abc123", "subnet-def456"],
    security_group_ids=["sg-abc123"],
    route_table_ids=["rtb-abc123"],
    enable_s3=True,
    enable_glue=True,
    enable_athena=True
)

config = DataLakeConfig.from_toml("config.toml")
config.vpc_endpoints = vpc_config

session_factory = SessionFactory(region=config.region)
deployer = DataLakeDeployer(session_factory)
summary = deployer.deploy(config)
```

## Testing changes locally

Run python -m compileall src for a quick syntax check. Integration validation requires AWS credentials with permissions for S3, IAM, Glue, Firehose, Athena, and optionally KMS.
