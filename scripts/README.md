# Scripts

This directory contains utility and setup scripts for the Azure-OpenAI Stock Analysis Tool project.

## Available Scripts

### Setup Scripts

#### `setup_localstack.sh`
Automated LocalStack setup and verification script.

**Purpose**: Sets up LocalStack container with AWS services for local development.

**Features**:
- Detects both `docker-compose` (standalone) and `docker compose` (plugin) versions
- Starts LocalStack container with all required AWS services
- Initializes S3 buckets, DynamoDB tables, SQS queues, and SNS topics
- Attempts to install `awslocal` CLI (optional, graceful degradation)
- Verifies all AWS resources are properly created

**Usage**:
```bash
./scripts/setup_localstack.sh
```

**Prerequisites**:
- Docker and Docker Compose installed
- Port 4566 available for LocalStack

---

#### `setup_dashboard.sh`
Dashboard setup script.

**Purpose**: Sets up and configures the dashboard components.

**Usage**:
```bash
./scripts/setup_dashboard.sh
```

---

### Verification Scripts

#### `verify_aws_resources.py`
AWS resource verification script (no awslocal dependency).

**Purpose**: Verifies that all AWS resources in LocalStack are properly created and accessible.

**Features**:
- Checks S3 buckets exist and are accessible
- Verifies DynamoDB tables are created with correct schemas
- Confirms SQS queues are operational
- Tests SNS topics are configured
- Validates CloudWatch is accessible
- Color-coded output (✅/❌) for easy verification

**Usage**:
```bash
python scripts/verify_aws_resources.py
```

**Prerequisites**:
- LocalStack running (`docker-compose up -d`)
- boto3 installed (`pip install boto3`)

---

## Running Scripts from Project Root

All scripts can be run from the project root directory:

```bash
# Setup LocalStack
./scripts/setup_localstack.sh

# Setup Dashboard
./scripts/setup_dashboard.sh

# Verify AWS resources
python scripts/verify_aws_resources.py
```

## Script Permissions

Make sure shell scripts are executable:

```bash
chmod +x scripts/setup_localstack.sh
chmod +x scripts/setup_dashboard.sh
```

## Environment Variables

Scripts may require environment variables defined in `.env`:

```bash
# AWS LocalStack Configuration
USE_LOCALSTACK=true
AWS_ENDPOINT_URL=http://localhost:4566
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

## Troubleshooting

### Docker Compose Not Found
If you see "docker-compose: command not found":
- Install Docker Compose plugin: `sudo apt-get install docker-compose-plugin`
- Or install standalone: `sudo apt-get install docker-compose`
- Script automatically detects both versions

### Port 4566 Already in Use
If LocalStack fails to start:
```bash
# Check what's using the port
sudo lsof -i :4566

# Stop LocalStack
docker-compose down

# Start again
./scripts/setup_localstack.sh
```

### AWS Resources Not Created
If verification fails:
```bash
# Check LocalStack logs
docker-compose logs localstack

# Restart LocalStack
docker-compose down && docker-compose up -d

# Re-run initialization
./scripts/setup_localstack.sh
```

## Contributing

When adding new scripts:
1. Use descriptive filenames
2. Add proper error handling and validation
3. Include usage instructions in script comments
4. Make shell scripts executable
5. Update this README with the new script details
6. Test scripts on clean environment before committing
