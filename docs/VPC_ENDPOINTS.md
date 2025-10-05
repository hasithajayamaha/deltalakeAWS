# VPC Endpoints Configuration Guide

## Overview

VPC endpoints allow you to privately connect your VPC to AWS services without requiring an internet gateway, NAT device, VPN connection, or AWS Direct Connect. This feature enhances security by keeping traffic within the AWS network.

## Supported Services

The deltalake-aws package supports VPC endpoints for:

1. **Amazon S3** (Gateway Endpoint)
   - Provides private access to S3 buckets
   - Uses route tables for routing
   - No additional charges

2. **AWS Glue** (Interface Endpoint)
   - Private access to Glue Data Catalog
   - Uses Elastic Network Interfaces (ENIs)
   - Charged per hour and per GB processed

3. **Amazon Athena** (Interface Endpoint)
   - Private access to Athena query service
   - Uses Elastic Network Interfaces (ENIs)
   - Charged per hour and per GB processed

## Configuration

### Basic Configuration

Add the `vpc_endpoints` section to your TOML configuration:

```toml
[datalake.vpc_endpoints]
vpc_id = "vpc-0123456789abcdef0"
subnet_ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
security_group_ids = ["sg-0123456789abcdef0"]
route_table_ids = ["rtb-0123456789abcdef0"]
enable_s3 = true
enable_glue = true
enable_athena = true
enable_dns_support = true
enable_private_dns = true
```

### Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vpc_id` | string | Yes | - | The VPC ID where endpoints will be created |
| `subnet_ids` | list[string] | No | [] | Subnet IDs for interface endpoints (Glue, Athena) |
| `security_group_ids` | list[string] | No | [] | Security group IDs for interface endpoints |
| `route_table_ids` | list[string] | No | [] | Route table IDs for gateway endpoint (S3) |
| `enable_s3` | boolean | No | true | Enable S3 gateway endpoint |
| `enable_glue` | boolean | No | true | Enable Glue interface endpoint |
| `enable_athena` | boolean | No | true | Enable Athena interface endpoint |
| `enable_dns_support` | boolean | No | true | Enable DNS support for endpoints |
| `enable_private_dns` | boolean | No | true | Enable private DNS for interface endpoints |

## Prerequisites

### 1. VPC Setup

Ensure you have:
- A VPC with appropriate CIDR blocks
- Subnets in multiple availability zones (recommended)
- Route tables configured
- Security groups with appropriate rules

### 2. Security Group Rules

For interface endpoints (Glue, Athena), your security group should allow:

**Inbound Rules:**
```
Type: HTTPS
Protocol: TCP
Port: 443
Source: Your VPC CIDR or specific security groups
```

**Outbound Rules:**
```
Type: All traffic
Protocol: All
Port: All
Destination: 0.0.0.0/0 (or more restrictive as needed)
```

### 3. IAM Permissions

The AWS credentials used must have permissions for:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpoints",
        "ec2:ModifyVpcEndpoint",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
```

## Usage Examples

### Example 1: S3 Gateway Endpoint Only

```toml
[datalake.vpc_endpoints]
vpc_id = "vpc-abc123"
route_table_ids = ["rtb-abc123", "rtb-def456"]
enable_s3 = true
enable_glue = false
enable_athena = false
```

### Example 2: All Services with Multiple Subnets

```toml
[datalake.vpc_endpoints]
vpc_id = "vpc-abc123"
subnet_ids = [
  "subnet-abc123",  # us-east-1a
  "subnet-def456",  # us-east-1b
  "subnet-ghi789"   # us-east-1c
]
security_group_ids = ["sg-abc123"]
route_table_ids = ["rtb-abc123"]
enable_s3 = true
enable_glue = true
enable_athena = true
enable_private_dns = true
```

### Example 3: Python API

```python
from datalake_aws import (
    DataLakeConfig,
    VpcEndpointConfig,
    SessionFactory,
    DataLakeDeployer
)

# Create VPC endpoint configuration
vpc_config = VpcEndpointConfig(
    vpc_id="vpc-0123456789abcdef0",
    subnet_ids=["subnet-abc123", "subnet-def456"],
    security_group_ids=["sg-abc123"],
    route_table_ids=["rtb-abc123"],
    enable_s3=True,
    enable_glue=True,
    enable_athena=True,
    enable_private_dns=True
)

# Load base configuration and add VPC endpoints
config = DataLakeConfig.from_toml("config.toml")
config.vpc_endpoints = vpc_config

# Deploy
session_factory = SessionFactory(region=config.region)
deployer = DataLakeDeployer(session_factory)
summary = deployer.deploy(config)

print(f"VPC Endpoints: {summary.get('vpc_endpoints', 'not configured')}")
```

## Endpoint Types

### Gateway Endpoints (S3)

- **Routing**: Uses route tables to direct traffic
- **Cost**: Free
- **DNS**: Uses public DNS names
- **Best for**: S3 access from EC2, Lambda, etc.

### Interface Endpoints (Glue, Athena)

- **Routing**: Uses Elastic Network Interfaces (ENIs)
- **Cost**: Hourly charge + data processing charges
- **DNS**: Can use private DNS names
- **Best for**: Services requiring private connectivity

## Troubleshooting

### Issue: Endpoint creation fails

**Solution**: Check that:
1. VPC ID is correct and exists
2. Subnet IDs are in the same VPC
3. Security groups allow HTTPS (443) traffic
4. IAM permissions are sufficient

### Issue: Cannot access S3 through endpoint

**Solution**: Verify:
1. Route tables are correctly associated with subnets
2. S3 bucket policies don't block VPC endpoint access
3. VPC endpoint policy allows required actions

### Issue: Glue/Athena endpoint not working

**Solution**: Check:
1. Private DNS is enabled
2. Security groups allow inbound HTTPS
3. Subnets have proper routing
4. DNS resolution is working in VPC

## Best Practices

1. **High Availability**: Deploy interface endpoints in multiple availability zones
2. **Security Groups**: Use dedicated security groups for VPC endpoints
3. **Monitoring**: Enable VPC Flow Logs to monitor endpoint traffic
4. **Cost Optimization**: Use S3 gateway endpoints (free) when possible
5. **Tagging**: Apply consistent tags for resource management

## Cost Considerations

### S3 Gateway Endpoint
- **Cost**: Free
- **Data Transfer**: Standard S3 data transfer charges apply

### Glue Interface Endpoint
- **Hourly Charge**: ~$0.01 per hour per AZ
- **Data Processing**: ~$0.01 per GB processed
- **Example**: 2 AZs × 730 hours = ~$14.60/month + data charges

### Athena Interface Endpoint
- **Hourly Charge**: ~$0.01 per hour per AZ
- **Data Processing**: ~$0.01 per GB processed
- **Example**: 2 AZs × 730 hours = ~$14.60/month + data charges

## Additional Resources

- [AWS VPC Endpoints Documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [S3 Gateway Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)
- [Interface Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpce-interface.html)
- [VPC Endpoint Pricing](https://aws.amazon.com/privatelink/pricing/)
