# deltalake-aws Architecture

This document describes the architecture of the deltalake-aws package, including its components, data flow, and AWS resource relationships.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          deltalake-aws Package                               │
│                                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐                │
│  │   CLI       │─────▶│  Deployer    │─────▶│   AWS       │                │
│  │  (cli.py)   │      │(deployer.py) │      │  Services   │                │
│  └─────────────┘      └──────────────┘      └─────────────┘                │
│         │                     │                      │                       │
│         │                     │                      │                       │
│         ▼                     ▼                      ▼                       │
│  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐                │
│  │   Config    │      │    State     │      │  Sessions   │                │
│  │ (config.py) │      │  (state.py)  │      │(sessions.py)│                │
│  └─────────────┘      └──────────────┘      └─────────────┘                │
│         │                     │                      │                       │
│         ▼                     │                      │                       │
│  ┌─────────────┐              │                      │                       │
│  │ Validators  │              │                      │                       │
│  │(validators  │              │                      │                       │
│  │    .py)     │              │                      │                       │
│  └─────────────┘              │                      │                       │
│         │                     │                      │                       │
│         ▼                     ▼                      │                       │
│  ┌─────────────┐      ┌──────────────┐              │                       │
│  │ Exceptions  │      │     Cost     │              │                       │
│  │(exceptions  │      │  Estimator   │              │                       │
│  │    .py)     │      │  (cost.py)   │              │                       │
│  └─────────────┘      └──────────────┘              │                       │
│                                                      │                       │
└──────────────────────────────────────────────────────┼───────────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   boto3/AWS     │
                                              │      API        │
                                              └─────────────────┘
```

## AWS Resources Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AWS Data Lake Architecture                         │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          VPC (Optional)                              │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │ VPC Endpoint │  │ VPC Endpoint │  │ VPC Endpoint │             │   │
│  │  │   (S3)       │  │   (Glue)     │  │  (Athena)    │             │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │   │
│  │         │                  │                  │                     │   │
│  └─────────┼──────────────────┼──────────────────┼─────────────────────┘   │
│            │                  │                  │                           │
│            ▼                  ▼                  ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        S3 Bucket                                     │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  Prefixes:                                                  │    │   │
│  │  │  • raw/          - Raw ingested data                        │    │   │
│  │  │  • processed/    - Transformed data                         │    │   │
│  │  │  • analytics/    - Analytics-ready data                     │    │   │
│  │  │  • logs/         - Access logs                              │    │   │
│  │  │                                                              │    │   │
│  │  │  Features:                                                  │    │   │
│  │  │  ✓ Versioning enabled                                       │    │   │
│  │  │  ✓ Public access blocked                                    │    │   │
│  │  │  ✓ Access logging enabled                                   │    │   │
│  │  │  ✓ KMS encryption (optional)                                │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                 │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AWS Glue Data Catalog                             │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  • Database: analytics_catalog                              │    │   │
│  │  │  • Tables: Iceberg/Delta tables                             │    │   │
│  │  │  • Crawler: Auto-discovery (optional)                       │    │   │
│  │  │  • Lake Formation: Fine-grained access (optional)           │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                 │
│            │                                                                 │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Amazon Athena                                   │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  • Workgroup: datalake-workgroup                            │    │   │
│  │  │  • Query results: s3://bucket/analytics/athena-results/     │    │   │
│  │  │  • Encryption: SSE-S3 or SSE-KMS                            │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              Kinesis Data Firehose (Optional)                        │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  • Stream: raw-events                                       │    │   │
│  │  │  • Destination: S3 raw/ prefix                              │    │   │
│  │  │  • Compression: GZIP                                        │    │   │
│  │  │  • Buffering: 5 MiB / 300 seconds                           │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    IAM Roles & Policies                              │   │
│  │  ┌────────────────────────────────────────────────────────────┐    │   │
│  │  │  • Firehose Role: S3 write access                           │    │   │
│  │  │  • Crawler Role: S3 read, Glue write                        │    │   │
│  │  │  • Processing Role: Custom for Databricks/EMR/Glue          │    │   │
│  │  │  • Lake Formation Role: S3 access for LF                    │    │   │
│  │  └────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### Core Components

#### 1. **CLI (cli.py)**
- Entry point for command-line usage
- Parses arguments and configuration
- Orchestrates deployment workflow
- Handles cost estimation, drift detection, and history

**Key Functions:**
- `main()` - Main entry point
- `_build_parser()` - CLI argument parser
- `_resolve_credentials()` - AWS credentials resolution

#### 2. **Config (config.py)**
- Configuration data models using dataclasses
- TOML file parsing
- Automatic validation via `__post_init__()`

**Key Classes:**
- `DataLakeConfig` - Main configuration
- `FirehoseConfig` - Kinesis Firehose settings
- `IamRoleConfig` - IAM role definitions
- `VpcEndpointConfig` - VPC endpoint settings
- `LakeFormationConfig` - Lake Formation settings

#### 3. **Deployer (deployer.py)**
- Core deployment logic
- AWS resource provisioning
- Idempotent operations (create or update)
- Integrated with state management

**Key Methods:**
- `deploy()` - Main deployment orchestration
- `_ensure_bucket()` - S3 bucket provisioning
- `_ensure_glue_database()` - Glue database setup
- `_ensure_athena_workgroup()` - Athena configuration
- `_ensure_vpc_endpoints()` - VPC endpoint creation
- `_ensure_lake_formation()` - Lake Formation setup

#### 4. **Validators (validators.py)**
- Input validation functions
- AWS naming rule enforcement
- Data normalization

**Key Functions:**
- `validate_bucket_name()` - S3 bucket naming rules
- `validate_region()` - AWS region format
- `validate_database_name()` - Glue database rules
- `validate_arn()` - ARN format validation
- `validate_tags()` - Tag validation

#### 5. **Exceptions (exceptions.py)**
- Custom exception hierarchy
- Retry decorators for AWS throttling
- Error handling utilities

**Key Classes/Functions:**
- `DataLakeError` - Base exception
- `ValidationError` - Configuration errors
- `DeploymentError` - Deployment failures
- `@retry_on_throttle` - Retry decorator
- `@handle_client_error` - Error wrapper

#### 6. **State Manager (state.py)**
- Deployment state tracking
- Configuration drift detection
- Deployment history

**Key Methods:**
- `save_deployment()` - Record deployment
- `detect_drift()` - Find configuration changes
- `get_deployment_history()` - Retrieve history
- `get_last_successful_deployment()` - Last success

#### 7. **Cost Estimator (cost.py)**
- Monthly cost estimation
- Multiple usage scenarios
- Service-by-service breakdown

**Key Classes:**
- `CostEstimator` - Cost calculation engine
- `CostEstimate` - Cost result with breakdown

#### 8. **Sessions (sessions.py)**
- AWS session management
- boto3 client factory
- Credential handling

**Key Class:**
- `SessionFactory` - Creates boto3 sessions and clients

## Data Flow

### Deployment Flow

```
1. User Input
   ├─ CLI arguments
   └─ TOML configuration file
        │
        ▼
2. Configuration Loading
   ├─ Parse TOML
   ├─ Validate inputs
   └─ Create DataLakeConfig
        │
        ▼
3. State Check (if enabled)
   ├─ Load previous state
   ├─ Detect drift
   └─ Warn user of changes
        │
        ▼
4. Deployment Execution
   ├─ Create/update VPC endpoints
   ├─ Create/update S3 bucket
   ├─ Create/update Glue database
   ├─ Create/update IAM roles
   ├─ Create/update Firehose stream
   ├─ Create/update Glue crawler
   ├─ Create/update Athena workgroup
   ├─ Create/update transactional tables
   └─ Configure Lake Formation
        │
        ▼
5. State Recording
   ├─ Save deployment record
   ├─ Update current config
   └─ Store resource status
        │
        ▼
6. Result Summary
   └─ Display resource status
```

### Cost Estimation Flow

```
1. User Request
   └─ --estimate-cost flag
        │
        ▼
2. Configuration Loading
   └─ Parse TOML config
        │
        ▼
3. Cost Calculation
   ├─ S3 storage costs
   ├─ S3 request costs
   ├─ Glue catalog costs
   ├─ Glue crawler costs (if configured)
   ├─ Athena query costs (if configured)
   ├─ Firehose costs (if configured)
   ├─ KMS costs (if configured)
   └─ VPC endpoint costs (if configured)
        │
        ▼
4. Scenario Generation
   ├─ Light usage (dev/test)
   ├─ Medium usage (small prod)
   └─ Heavy usage (large prod)
        │
        ▼
5. Display Results
   └─ Formatted cost breakdown
```

## Error Handling Strategy

```
┌─────────────────────────────────────────┐
│         AWS API Call                    │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    @retry_on_throttle decorator         │
│    • Catches throttling errors          │
│    • Exponential backoff (1s, 2s, 4s)   │
│    • Max 5 retries                      │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│   @handle_client_error decorator        │
│   • Catches ClientError                 │
│   • Logs detailed error info            │
│   • Wraps in DeploymentError            │
└─────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│      Exception Propagation              │
│      • State saved (success=False)      │
│      • User notified                    │
│      • Exit with error code             │
└─────────────────────────────────────────┘
```

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
│                                                               │
│  1. Input Validation                                         │
│     ├─ Bucket name validation                                │
│     ├─ ARN format validation                                 │
│     ├─ Tag validation                                        │
│     └─ Region validation                                     │
│                                                               │
│  2. S3 Bucket Security                                       │
│     ├─ Block all public access                               │
│     ├─ Versioning enabled                                    │
│     ├─ Access logging enabled                                │
│     └─ KMS encryption (optional)                             │
│                                                               │
│  3. IAM Least Privilege                                      │
│     ├─ Service-specific roles                                │
│     ├─ Minimal permissions                                   │
│     └─ Resource-level restrictions                           │
│                                                               │
│  4. Network Security (Optional)                              │
│     ├─ VPC endpoints for private access                      │
│     ├─ Security groups                                       │
│     └─ No internet gateway required                          │
│                                                               │
│  5. Data Governance (Optional)                               │
│     ├─ Lake Formation fine-grained access                    │
│     ├─ Column-level security                                 │
│     └─ Audit logging                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Patterns

### Pattern 1: Basic Data Lake
```
S3 Bucket → Glue Database → Athena Workgroup
```

### Pattern 2: Streaming Data Lake
```
Kinesis Firehose → S3 Bucket → Glue Crawler → Glue Database → Athena
```

### Pattern 3: Secure Private Data Lake
```
VPC Endpoints → S3 Bucket → Glue Database → Athena
                    ↓
              Lake Formation
```

### Pattern 4: Processing-Ready Data Lake
```
S3 Bucket → Glue Database → Processing Role (Databricks/EMR/Glue)
```

## Extension Points

The architecture is designed for extensibility:

1. **New AWS Services**: Add methods to `DataLakeDeployer`
2. **Custom Validators**: Add functions to `validators.py`
3. **New Cost Models**: Extend `CostEstimator.PRICING`
4. **Additional State**: Extend `StateManager` state structure
5. **New CLI Commands**: Add arguments to `_build_parser()`

## Performance Considerations

1. **Parallel Resource Creation**: Independent resources could be created concurrently
2. **Caching**: boto3 clients are reused via `SessionFactory`
3. **Retry Strategy**: Exponential backoff prevents API throttling
4. **State Management**: JSON file I/O is minimal and efficient

## Testing Strategy

```
┌─────────────────────────────────────────┐
│         Testing Pyramid                 │
│                                          │
│            ┌─────────┐                  │
│            │   E2E   │                  │
│            │  Tests  │                  │
│            └─────────┘                  │
│          ┌─────────────┐                │
│          │ Integration │                │
│          │    Tests    │                │
│          └─────────────┘                │
│      ┌───────────────────┐              │
│      │   Unit Tests      │              │
│      │  (validators,     │              │
│      │   config, etc.)   │              │
│      └───────────────────┘              │
│                                          │
└─────────────────────────────────────────┘
```

Current test coverage:
- ✅ Unit tests for validators (40+ tests)
- ✅ Unit tests for config (15+ tests)
- 🔄 Integration tests (future: using moto)
- 🔄 E2E tests (future: real AWS account)

## Monitoring & Observability

1. **Logging**: Comprehensive logging at INFO/DEBUG levels
2. **State Tracking**: Deployment history and status
3. **Drift Detection**: Configuration change tracking
4. **Cost Visibility**: Pre-deployment cost estimation

## Future Architecture Enhancements

1. **Parallel Deployment**: Use ThreadPoolExecutor for independent resources
2. **Progress Bars**: Real-time deployment progress with tqdm
3. **Rollback**: Automatic rollback on deployment failure
4. **Resource Tagging**: Automatic tagging with deployment metadata
5. **Multi-Region**: Support for multi-region deployments
6. **Terraform Export**: Generate Terraform from configuration
