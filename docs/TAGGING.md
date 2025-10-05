# Resource Tagging Guide

## Overview

The deltalake-aws package supports comprehensive resource tagging across all AWS resources it creates. Tags are automatically propagated to all supported resources, enabling better cost tracking, resource organization, and governance.

## Supported Resources

Tags are automatically applied to the following resources:

1. **S3 Buckets** ✓
2. **Glue Databases** ✓
3. **Glue Crawlers** ✓
4. **Glue Tables** (transactional tables)
5. **Athena Workgroups** ✓
6. **IAM Roles** ✓
7. **Kinesis Data Firehose Streams** ✓
8. **VPC Endpoints** ✓

## Configuration

### TOML Configuration

Add tags in the `[datalake.tags]` section of your configuration file:

```toml
[datalake]
region = "us-east-1"
bucket_name = "my-data-lake"
glue_database = "analytics_catalog"

[datalake.tags]
Environment = "production"
Owner = "data-engineering"
Project = "analytics-platform"
CostCenter = "engineering"
ManagedBy = "deltalake-aws"
```

### Python API

```python
from datalake_aws import DataLakeConfig, SessionFactory, DataLakeDeployer

config = DataLakeConfig.from_toml("config.toml")

# Or set tags programmatically
config.tags = {
    "Environment": "production",
    "Owner": "data-engineering",
    "Project": "analytics-platform",
    "CostCenter": "engineering",
    "ManagedBy": "deltalake-aws"
}

session_factory = SessionFactory(region=config.region)
deployer = DataLakeDeployer(session_factory)
summary = deployer.deploy(config)
```

## Tag Propagation Behavior

### Create Operations
When creating new resources, tags are applied immediately:
- S3 buckets: Applied via `put_bucket_tagging`
- Glue resources: Applied via `tag_resource` API
- Athena workgroups: Applied via `Tags` parameter
- IAM roles: Applied via `Tags` parameter
- Firehose streams: Applied via `Tags` parameter
- VPC endpoints: Applied via `TagSpecifications`

### Update Operations
When updating existing resources, tags are refreshed:
- **S3 buckets**: Tags are updated on every deployment
- **Glue databases**: Tags are updated if they exist
- **Glue crawlers**: Tags are updated on crawler updates
- **Athena workgroups**: Tags are updated on workgroup updates
- **IAM roles**: Old tags are removed and new tags are applied
- **Firehose streams**: Tags are updated if stream exists
- **VPC endpoints**: Tags are applied during creation only

## Best Practices

### 1. Consistent Naming Convention
Use consistent tag keys across all resources:
```toml
[datalake.tags]
Environment = "prod"  # Not "Env" or "environment"
Owner = "team-name"   # Not "owner" or "Team"
```

### 2. Required Tags
Consider making certain tags mandatory for governance:
- **Environment**: prod, staging, dev
- **Owner**: Team or individual responsible
- **CostCenter**: For cost allocation
- **Project**: Project or application name

### 3. Automation Tags
Include tags that identify automated deployments:
```toml
[datalake.tags]
ManagedBy = "deltalake-aws"
DeploymentMethod = "automated"
Version = "1.0.0"
```

### 4. Compliance Tags
Add tags for compliance and security:
```toml
[datalake.tags]
DataClassification = "confidential"
ComplianceScope = "pci-dss"
BackupRequired = "true"
```

## Common Tag Schemas

### Basic Schema
```toml
[datalake.tags]
Environment = "production"
Owner = "data-team"
Project = "analytics"
```

### Enterprise Schema
```toml
[datalake.tags]
Environment = "production"
Owner = "data-engineering@company.com"
Project = "customer-analytics"
CostCenter = "CC-12345"
BusinessUnit = "marketing"
ManagedBy = "deltalake-aws"
DataClassification = "internal"
BackupPolicy = "daily"
ComplianceScope = "gdpr,ccpa"
```

### Multi-Environment Schema
```toml
# Production
[datalake.tags]
Environment = "production"
Owner = "data-team"
Project = "analytics"
Tier = "critical"
SLA = "99.9"

# Development
[datalake.tags]
Environment = "development"
Owner = "data-team"
Project = "analytics"
Tier = "non-critical"
AutoShutdown = "true"
```

## Cost Allocation

### Using Tags for Cost Tracking

Tags enable detailed cost tracking in AWS Cost Explorer:

1. **Activate Cost Allocation Tags** in AWS Billing Console
2. **Wait 24 hours** for tags to appear in Cost Explorer
3. **Create Cost Reports** filtered by tags

Example cost allocation tags:
```toml
[datalake.tags]
CostCenter = "engineering"
Project = "data-lake"
Environment = "production"
```

### Cost Optimization Tips

1. **Tag all resources consistently** for accurate cost attribution
2. **Use Environment tags** to track costs per environment
3. **Include Project tags** for project-level cost tracking
4. **Add CostCenter tags** for departmental chargeback

## Tag Limitations

### AWS Tag Limits
- **Maximum tags per resource**: 50
- **Key length**: 1-128 characters
- **Value length**: 0-256 characters
- **Allowed characters**: Letters, numbers, spaces, and `+ - = . _ : / @`

### Service-Specific Considerations

#### S3 Buckets
- Tags are applied at bucket level, not object level
- Maximum 50 tags per bucket
- Tags don't affect bucket policies

#### Glue Resources
- Tags are applied to databases, crawlers, and tables
- Tags can be used in IAM policies for access control
- Maximum 50 tags per resource

#### IAM Roles
- Tags can be used in IAM policies
- Session tags can be passed during role assumption
- Maximum 50 tags per role

#### VPC Endpoints
- Tags are applied during creation
- Cannot be modified after creation (must recreate)
- Maximum 50 tags per endpoint

## Troubleshooting

### Issue: Tags not appearing on resources

**Possible causes:**
1. Insufficient IAM permissions
2. Tag keys contain invalid characters
3. Exceeded maximum tag limit (50 per resource)

**Solution:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutBucketTagging",
        "glue:TagResource",
        "athena:TagResource",
        "iam:TagRole",
        "firehose:TagDeliveryStream",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

### Issue: Tags not updating on existing resources

**Solution:**
The deployer automatically updates tags on existing resources during deployment. If tags aren't updating:
1. Check IAM permissions for tagging operations
2. Verify the resource supports tag updates
3. Check CloudTrail logs for tagging API errors

### Issue: Cost allocation tags not showing in Cost Explorer

**Solution:**
1. Activate tags in AWS Billing Console
2. Wait 24 hours for tags to propagate
3. Ensure tags are applied to all resources
4. Verify tag keys are consistent across resources

## Examples

### Example 1: Multi-Environment Setup

```toml
# production.toml
[datalake]
region = "us-east-1"
bucket_name = "prod-data-lake"
glue_database = "prod_analytics"

[datalake.tags]
Environment = "production"
Owner = "data-team"
CostCenter = "CC-001"
Tier = "critical"
```

```toml
# development.toml
[datalake]
region = "us-east-1"
bucket_name = "dev-data-lake"
glue_database = "dev_analytics"

[datalake.tags]
Environment = "development"
Owner = "data-team"
CostCenter = "CC-001"
Tier = "non-critical"
AutoShutdown = "enabled"
```

### Example 2: Compliance-Focused Tagging

```toml
[datalake.tags]
Environment = "production"
DataClassification = "confidential"
ComplianceScope = "pci-dss,sox"
EncryptionRequired = "true"
RetentionPeriod = "7years"
BackupFrequency = "daily"
Owner = "compliance-team@company.com"
```

### Example 3: Project-Based Tagging

```toml
[datalake.tags]
Project = "customer-360"
Team = "customer-analytics"
Stakeholder = "marketing-vp"
Budget = "Q1-2025"
Priority = "high"
DeploymentDate = "2025-01-15"
```

## Additional Resources

- [AWS Tagging Best Practices](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html)
- [AWS Cost Allocation Tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html)
- [Tag Policies in AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)
