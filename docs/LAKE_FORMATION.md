# AWS Lake Formation Integration Guide

## Overview

AWS Lake Formation provides centralized, fine-grained access control for data lakes. This integration enables column-level security, row-level filtering, and centralized permissions management across your data lake resources.

## Features

The deltalake-aws Lake Formation integration provides:

1. **Centralized Access Control**: Manage permissions from a single location
2. **Fine-Grained Permissions**: Control access at database, table, and column levels
3. **Data Lake Administrators**: Designate administrators with full access
4. **S3 Location Registration**: Register S3 buckets with Lake Formation
5. **Permission Grants**: Automatically grant permissions to principals
6. **Glue Integration**: Configure Glue databases to use Lake Formation permissions

## Configuration

### Basic Configuration

```toml
[datalake.lake_formation]
enable_lake_formation = true
register_s3_location = true
use_lake_formation_credentials = true
data_lake_admins = ["DataLakeAdmin"]
```

### Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `enable_lake_formation` | boolean | No | false | Enable Lake Formation integration |
| `data_lake_admins` | list[string] | No | [] | IAM roles/ARNs with admin access |
| `register_s3_location` | boolean | No | true | Register S3 bucket with Lake Formation |
| `use_lake_formation_credentials` | boolean | No | true | Use Lake Formation for Glue permissions |
| `permissions` | list[object] | No | [] | Permission grants to configure |

### Permission Configuration

Each permission grant requires:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `principal` | string | Yes | IAM role/user ARN |
| `resource_type` | string | Yes | DATABASE, TABLE, or DATA_LOCATION |
| `database_name` | string | Conditional | Database name (for DATABASE/TABLE) |
| `table_name` | string | Conditional | Table name (for specific TABLE) |
| `table_wildcard` | boolean | No | Grant on all tables in database |
| `permissions` | list[string] | Yes | Permissions to grant |
| `permissions_with_grant_option` | list[string] | No | Permissions that can be re-granted |

## Permission Types

### Database Permissions
- `DESCRIBE`: View database metadata
- `CREATE_TABLE`: Create tables in the database
- `ALTER`: Modify database properties
- `DROP`: Delete the database

### Table Permissions
- `SELECT`: Query table data
- `INSERT`: Add data to table
- `DELETE`: Remove data from table
- `DESCRIBE`: View table metadata
- `ALTER`: Modify table structure
- `DROP`: Delete the table

### Data Location Permissions
- `DATA_LOCATION_ACCESS`: Access S3 location

## Usage Examples

### Example 1: Basic Setup with Admins

```toml
[datalake.lake_formation]
enable_lake_formation = true
data_lake_admins = [
  "DataLakeAdmin",
  "arn:aws:iam::123456789012:role/AdminRole"
]
```

### Example 2: Read-Only Analyst Access

```toml
[datalake.lake_formation]
enable_lake_formation = true
data_lake_admins = ["DataLakeAdmin"]

# Database describe permission
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataAnalyst"
resource_type = "DATABASE"
database_name = "analytics_catalog"
permissions = ["DESCRIBE"]

# Read access to all tables
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataAnalyst"
resource_type = "TABLE"
database_name = "analytics_catalog"
table_wildcard = true
permissions = ["SELECT", "DESCRIBE"]
```

### Example 3: Data Engineer with Full Access

```toml
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataEngineer"
resource_type = "DATABASE"
database_name = "analytics_catalog"
permissions = ["DESCRIBE", "CREATE_TABLE", "ALTER"]

[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataEngineer"
resource_type = "TABLE"
database_name = "analytics_catalog"
table_wildcard = true
permissions = ["SELECT", "INSERT", "DELETE", "DESCRIBE", "ALTER", "DROP"]

[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataEngineer"
resource_type = "DATA_LOCATION"
permissions = ["DATA_LOCATION_ACCESS"]
```

### Example 4: Specific Table Access

```toml
# Access to specific sensitive table
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/ComplianceTeam"
resource_type = "TABLE"
database_name = "analytics_catalog"
table_name = "customer_pii"
permissions = ["SELECT", "DESCRIBE"]
```

### Example 5: Grant Option for Delegation

```toml
# Allow DataEngineer to grant SELECT to others
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataEngineer"
resource_type = "TABLE"
database_name = "analytics_catalog"
table_name = "public_data"
permissions = ["SELECT", "DESCRIBE"]
permissions_with_grant_option = ["SELECT"]
```

## Python API Usage

```python
from datalake_aws import (
    DataLakeConfig,
    LakeFormationConfig,
    LakeFormationPermission,
    SessionFactory,
    DataLakeDeployer
)

# Create Lake Formation configuration
lf_config = LakeFormationConfig(
    enable_lake_formation=True,
    data_lake_admins=["DataLakeAdmin"],
    register_s3_location=True,
    use_lake_formation_credentials=True,
    permissions=[
        LakeFormationPermission(
            principal="arn:aws:iam::123456789012:role/DataAnalyst",
            resource_type="DATABASE",
            database_name="analytics_catalog",
            permissions=["DESCRIBE"]
        ),
        LakeFormationPermission(
            principal="arn:aws:iam::123456789012:role/DataAnalyst",
            resource_type="TABLE",
            database_name="analytics_catalog",
            table_wildcard=True,
            permissions=["SELECT", "DESCRIBE"]
        )
    ]
)

# Load config and add Lake Formation
config = DataLakeConfig.from_toml("config.toml")
config.lake_formation = lf_config

# Deploy
session_factory = SessionFactory(region=config.region)
deployer = DataLakeDeployer(session_factory)
summary = deployer.deploy(config)

print(f"Lake Formation: {summary.get('lake_formation', 'not configured')}")
```

## How It Works

### 1. Data Lake Administrators

Administrators are configured in Lake Formation settings:
- Full access to all data lake resources
- Can grant permissions to other principals
- Bypass IAM-based access controls

### 2. S3 Location Registration

The S3 bucket is registered with Lake Formation:
- Creates a service role for Lake Formation
- Registers the bucket ARN
- Enables Lake Formation to manage access

### 3. Database Configuration

Glue database is updated to use Lake Formation:
- Disables default IAM permissions
- Requires explicit Lake Formation grants
- Enables fine-grained access control

### 4. Permission Grants

Permissions are granted through Lake Formation:
- Database-level permissions
- Table-level permissions (specific or wildcard)
- Data location permissions
- Optional grant options for delegation

## IAM Requirements

### Deployer Permissions

The AWS credentials used must have:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lakeformation:GetDataLakeSettings",
        "lakeformation:PutDataLakeSettings",
        "lakeformation:RegisterResource",
        "lakeformation:ListResources",
        "lakeformation:GrantPermissions",
        "lakeformation:RevokePermissions",
        "lakeformation:ListPermissions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/*lakeformation*"
    }
  ]
}
```

### Principal Permissions

Principals accessing data need:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lakeformation:GetDataAccess"
      ],
      "Resource": "*"
    }
  ]
}
```

## Best Practices

### 1. Start with Administrators

Always configure data lake administrators first:
```toml
data_lake_admins = ["DataLakeAdmin", "BackupAdmin"]
```

### 2. Use Least Privilege

Grant only necessary permissions:
```toml
# Good: Specific permissions
permissions = ["SELECT", "DESCRIBE"]

# Avoid: Overly broad permissions
permissions = ["ALL"]
```

### 3. Leverage Table Wildcards

For consistent access across tables:
```toml
table_wildcard = true
permissions = ["SELECT", "DESCRIBE"]
```

### 4. Document Permission Grants

Use comments to explain grants:
```toml
# Analytics team read-only access
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/AnalyticsTeam"
resource_type = "TABLE"
table_wildcard = true
permissions = ["SELECT", "DESCRIBE"]
```

### 5. Use Grant Options Carefully

Only grant delegation rights when necessary:
```toml
permissions_with_grant_option = ["SELECT"]  # Allow re-granting SELECT only
```

## Migration from IAM-Only

### Step 1: Enable Lake Formation

```toml
[datalake.lake_formation]
enable_lake_formation = true
use_lake_formation_credentials = true
```

### Step 2: Configure Administrators

```toml
data_lake_admins = ["CurrentAdminRole"]
```

### Step 3: Migrate Permissions

Convert IAM policies to Lake Formation grants:

**Before (IAM Policy):**
```json
{
  "Effect": "Allow",
  "Action": ["glue:GetTable", "glue:GetTables"],
  "Resource": "arn:aws:glue:*:*:table/analytics_catalog/*"
}
```

**After (Lake Formation):**
```toml
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/DataAnalyst"
resource_type = "TABLE"
database_name = "analytics_catalog"
table_wildcard = true
permissions = ["DESCRIBE"]
```

### Step 4: Test Access

Verify principals can access data through Lake Formation.

### Step 5: Remove IAM Policies

Once verified, remove redundant IAM policies.

## Troubleshooting

### Issue: Access Denied After Enabling Lake Formation

**Cause**: Default IAM permissions disabled

**Solution**: Grant explicit Lake Formation permissions:
```toml
[[datalake.lake_formation.permissions]]
principal = "arn:aws:iam::123456789012:role/YourRole"
resource_type = "DATABASE"
permissions = ["DESCRIBE"]
```

### Issue: Cannot Register S3 Location

**Cause**: Insufficient IAM permissions

**Solution**: Ensure deployer has `lakeformation:RegisterResource` permission

### Issue: Permissions Not Taking Effect

**Cause**: IAM policies overriding Lake Formation

**Solution**: 
1. Check for conflicting IAM policies
2. Ensure `use_lake_formation_credentials = true`
3. Verify database has default permissions disabled

### Issue: Admin Cannot Access Data

**Cause**: Admin not configured in Lake Formation

**Solution**: Add to data_lake_admins list:
```toml
data_lake_admins = ["YourAdminRole"]
```

## Advanced Features

### Column-Level Security

While not directly configured through this tool, Lake Formation supports column-level filtering. After deployment, use AWS Console or CLI to:

1. Grant table permissions with column filters
2. Specify allowed columns per principal
3. Apply data filters for row-level security

### Cross-Account Access

Lake Formation supports cross-account data sharing:

1. Configure Lake Formation in both accounts
2. Use Resource Access Manager (RAM) to share
3. Grant permissions to external account principals

### Audit and Compliance

Lake Formation integrates with CloudTrail:
- All permission changes logged
- Access attempts recorded
- Compliance reporting available

## Additional Resources

- [AWS Lake Formation Documentation](https://docs.aws.amazon.com/lake-formation/)
- [Lake Formation Best Practices](https://docs.aws.amazon.com/lake-formation/latest/dg/best-practices.html)
- [Lake Formation Permissions Reference](https://docs.aws.amazon.com/lake-formation/latest/dg/lake-formation-permissions-reference.html)
- [Cross-Account Access](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-access.html)
