# AWS Services Configuration Optimization Guide

## Overview

This guide explains how to optimize and expand your AWS documentation knowledge base for better threat modeling and security analysis.

## Quick Start

### 1. List Available Services

```bash
# List all services by category
make aws-list

# Or using the script directly
python scripts/aws_services_manager.py list --by-category
```

### 2. Update Config with High-Priority Services

```bash
# Preview what would be updated (dry run)
make aws-update

# Update config.yaml with high-priority services only
make aws-update-high

# Update with all services
python scripts/aws_services_manager.py update
```

### 3. Scrape and Ingest

```bash
# Scrape the configured services
make scrape

# Process and embed
make ingest

# Insert into database
make insert
```

## Service Priority Levels

Services are categorized by priority for security/threat modeling:

- **🔴 Critical**: Essential for security analysis (IAM, KMS)
- **🟠 High**: Important security services (S3, EC2, VPC, Security Hub, GuardDuty)
- **🟡 Medium**: Useful for comprehensive coverage (Lambda, RDS, CloudWatch)
- **🟢 Low**: Nice to have, less critical (EFS, Backup, SNS)

## Recommended Service Sets

### Minimal Set (Fast Setup)
For quick testing with essential services:
```bash
python scripts/aws_services_manager.py update --priority critical
```

**Services**: IAM, KMS

### Security-Focused Set (Recommended)
For comprehensive security analysis:
```bash
python scripts/aws_services_manager.py update --priority high
```

**Services**: 
- Core: S3, EC2, VPC
- IAM: IAM, KMS, Secrets Manager
- Security: Security Hub, GuardDuty, CloudTrail

### Comprehensive Set (Full Coverage)
For maximum knowledge base:
```bash
python scripts/aws_services_manager.py update
```

**All 25+ services** across all categories

## Configuration Structure

### Main Config (`config/config.yaml`)

The main config uses a simple list format:

```yaml
aws_docs:
  base_dir: "./aws_docs"
  max_workers: 4
  services:
    - name: "s3"
      url: "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    - name: "ec2"
      url: "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html"
```

### Extended Config (`config/aws_services.yaml`)

The extended config includes metadata for better management:

```yaml
core_infrastructure:
  - name: "s3"
    url: "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    priority: "high"
    security_focus: ["data-protection", "access-control", "encryption"]
```

## Optimization Strategies

### 1. Start Small, Expand Gradually

1. Begin with critical/high priority services
2. Test your pipeline
3. Gradually add more services as needed

### 2. Focus on Security-Relevant Services

For threat modeling, prioritize:
- **Identity & Access**: IAM, KMS, Secrets Manager
- **Security Services**: Security Hub, GuardDuty, WAF, Shield
- **Core Infrastructure**: S3, EC2, VPC (most common attack surfaces)
- **Monitoring**: CloudTrail, CloudWatch (for detection)

### 3. Optimize Scraping Performance

**Increase Workers** (if you have bandwidth):
```yaml
aws_docs:
  max_workers: 8  # Increase from 4
```

**Adjust Scraping Depth**:
- Current: `max_depth=1` (main pages only)
- For more coverage: Modify `aws_scraper.py` to increase depth

### 4. Selective Scraping

You can manually edit `config.yaml` to include only specific services:

```yaml
aws_docs:
  services:
    - name: "s3"
      url: "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html"
    - name: "iam"
      url: "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html"
    # Add only what you need
```

## Adding New Services

### Method 1: Edit Extended Config

1. Open `config/aws_services.yaml`
2. Add service to appropriate category:

```yaml
security_services:
  - name: "new-service"
    url: "https://docs.aws.amazon.com/NewService/latest/userguide/Welcome.html"
    priority: "high"
    security_focus: ["relevant", "topics"]
```

3. Update main config:
```bash
python scripts/aws_services_manager.py update
```

### Method 2: Direct Edit

Edit `config/config.yaml` directly:

```yaml
aws_docs:
  services:
    - name: "new-service"
      url: "https://docs.aws.amazon.com/NewService/latest/userguide/Welcome.html"
```

## Performance Considerations

### Storage
- Each service can generate 50-200+ document chunks
- 25 services ≈ 2,500-5,000 chunks
- Storage: ~500MB - 2GB (with embeddings)

### Scraping Time
- Per service: 5-15 minutes (depending on depth)
- High priority set (8 services): ~1-2 hours
- Full set (25 services): ~3-5 hours

### Embedding Cost
- OpenAI `text-embedding-3-small`: ~$0.02 per 1M tokens
- 5,000 chunks ≈ $0.10-0.50 (one-time cost)

## Best Practices

1. **Version Control**: Keep `aws_services.yaml` in git, exclude `config.yaml` (contains API keys)

2. **Incremental Updates**: Add services gradually and test

3. **Regular Refresh**: Re-scrape periodically to get latest docs:
   ```bash
   make scrape
   make ingest
   make insert
   ```

4. **Monitor Quality**: Check scraped content quality:
   ```bash
   ls -lh aws_docs/
   # Check file sizes and counts
   ```

5. **Filter by Use Case**: 
   - **Threat Modeling**: Focus on high-priority services
   - **Compliance**: Add Security Hub, CloudTrail
   - **Application Security**: Add Lambda, ECS, EKS

## Troubleshooting

### Service Not Scraping
- Check URL is accessible
- Verify service name doesn't conflict
- Check logs: `make scrape` output

### Too Many Documents
- Reduce `max_depth` in `aws_scraper.py`
- Use priority filtering: `--priority high`
- Manually edit config to remove services

### Scraping Too Slow
- Increase `max_workers` (but respect rate limits)
- Reduce `max_depth`
- Scrape in batches by priority

## Example Workflows

### Workflow 1: Security-Focused Setup
```bash
# 1. Update with high-priority services
make aws-update-high

# 2. Scrape
make scrape

# 3. Process
make ingest

# 4. Store
make insert
```

### Workflow 2: Add Single Service
```bash
# 1. Edit config/aws_services.yaml (add service)

# 2. Update main config
python scripts/aws_services_manager.py update

# 3. Scrape only new service (modify scraper to filter)

# 4. Process and insert
make ingest
make insert
```

## Next Steps

- Review scraped content quality
- Test queries against new services
- Expand based on your specific use cases
- Consider adding non-AWS sources (Kubernetes, Terraform, etc.)
