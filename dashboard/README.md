# DataLake Discovery Dashboard

A comprehensive web application for discovering, visualizing, and managing AWS data lake infrastructure deployed by deltalake-aws.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              React Frontend (Port 5173)                  │
│  • Dashboard • Architecture Viewer • Cost Analysis       │
│  • Resource Explorer • Deployment Manager • Monitoring   │
└─────────────────────────────────────────────────────────┘
                         │
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                   │
│  • Discovery • Cost Estimation • Deployment              │
│  • Monitoring • Configuration Management                 │
└─────────────────────────────────────────────────────────┘
                         │
                         │ boto3
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    AWS Services                          │
│  S3 • Glue • Athena • Firehose • IAM • VPC              │
└─────────────────────────────────────────────────────────┘
```

## 📋 Features

### ✅ Implemented (Backend)
- **Resource Discovery**: Discover all AWS data lake resources
  - S3 buckets with details (versioning, encryption, tags)
  - Glue databases and tables
  - Athena workgroups
  - Kinesis Firehose streams
  - IAM roles
  - VPC endpoints

- **Cost Estimation**: Monthly cost estimates
  - Multiple scenarios (Light, Medium, Heavy)
  - Service-by-service breakdown
  - Cost percentage analysis
  - Usage assumptions

- **API Documentation**: Auto-generated Swagger/OpenAPI docs at `/api/docs`

### 🚧 To Be Implemented
- **Deployment Management**: Trigger deployments, view history
- **Monitoring**: CloudWatch metrics, S3 access logs
- **Configuration Management**: TOML editor, validation
- **Frontend UI**: React components and pages

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- AWS credentials configured
- deltalake-aws package installed

### Backend Setup

```bash
# Navigate to backend directory
cd dashboard/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install deltalake-aws (from parent directory)
pip install -e ../../

# Set environment variables
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Run the server
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Frontend Setup

```bash
# Navigate to frontend directory
cd dashboard/frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env

# Run development server
npm run dev
```

The frontend will be available at: http://localhost:5173

## 📡 API Endpoints

### Discovery
```
GET  /api/v1/discover                    # Discover all resources
GET  /api/v1/resources/s3                # List S3 buckets
GET  /api/v1/resources/s3/{bucket_name}  # Get bucket details
GET  /api/v1/resources/glue/databases    # List Glue databases
GET  /api/v1/resources/glue/tables       # List Glue tables
GET  /api/v1/resources/athena/workgroups # List Athena workgroups
GET  /api/v1/resources/firehose/streams  # List Firehose streams
GET  /api/v1/resources/iam/roles         # List IAM roles
GET  /api/v1/resources/vpc/endpoints     # List VPC endpoints
```

### Cost Estimation
```
GET  /api/v1/cost/estimate    # Estimate costs
GET  /api/v1/cost/scenarios   # Get all cost scenarios
GET  /api/v1/cost/breakdown   # Get detailed cost breakdown
```

### Deployment (Stub)
```
GET  /api/v1/deploy/history   # Get deployment history
GET  /api/v1/deploy/status    # Get deployment status
POST /api/v1/deploy           # Trigger deployment
```

### Monitoring (Stub)
```
GET  /api/v1/metrics/s3       # Get S3 metrics
GET  /api/v1/metrics/athena   # Get Athena metrics
GET  /api/v1/logs/s3-access   # Get S3 access logs
```

### Configuration (Stub)
```
GET  /api/v1/config           # Get current config
POST /api/v1/config/validate  # Validate config
GET  /api/v1/config/templates # Get config templates
```

### Health
```
GET  /api/v1/health           # Health check
GET  /api/v1/version          # Get versions
```

## 🧪 Testing the API

### Using curl

```bash
# Discover all resources
curl http://localhost:8000/api/v1/discover

# List S3 buckets
curl http://localhost:8000/api/v1/resources/s3

# Get cost estimate (medium scenario)
curl "http://localhost:8000/api/v1/cost/estimate?scenario=medium"

# Get cost breakdown
curl "http://localhost:8000/api/v1/cost/breakdown?storage_gb=500&monthly_queries=1000"

# Health check
curl http://localhost:8000/api/v1/health
```

### Using Python

```python
import requests

# Discover resources
response = requests.get('http://localhost:8000/api/v1/discover')
data = response.json()
print(f"Found {data['summary']['total_resources']} resources")

# Get cost estimate
response = requests.get(
    'http://localhost:8000/api/v1/cost/estimate',
    params={'scenario': 'medium'}
)
cost_data = response.json()
print(f"Monthly cost: ${cost_data['monthly_cost']:.2f}")
```

## 🎨 Frontend Pages

### 1. Dashboard (/)
- Overview cards (resources, cost, status)
- Quick actions
- Recent activity timeline

### 2. Architecture Viewer (/architecture)
- Interactive diagram of AWS resources
- Click resources for details
- Real-time status indicators

### 3. Resource Explorer (/resources)
- Tabbed interface for each resource type
- Search and filter
- Export capabilities

### 4. Cost Analysis (/cost)
- Monthly cost breakdown
- Cost trends over time
- Scenario comparison
- Budget alerts

### 5. Deployment Manager (/deployment)
- Configuration editor
- Deployment history
- Drift detection
- Dry-run preview

### 6. Monitoring (/monitoring)
- CloudWatch metrics
- Access logs viewer
- Query performance
- Alerts

### 7. Settings (/settings)
- AWS credentials
- Region selection
- Preferences

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Manual Docker Build

```bash
# Backend
cd dashboard/backend
docker build -t datalake-api .
docker run -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  datalake-api

# Frontend
cd dashboard/frontend
docker build -t datalake-ui .
docker run -p 5173:5173 datalake-ui
```

## 🔧 Configuration

### Backend Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# API Configuration
DEBUG=false
CORS_ORIGINS=["http://localhost:5173"]

# State File
STATE_FILE_PATH=.datalake-state.json

# Database
DATABASE_URL=sqlite:///./datalake_dashboard.db

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### Frontend Environment Variables

```bash
# API URL
VITE_API_URL=http://localhost:8000/api/v1
```

## 📊 Example API Responses

### Discovery Response
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "region": "us-east-1",
  "resources": {
    "s3_buckets": [{
      "name": "my-data-lake",
      "creation_date": "2024-01-01T00:00:00",
      "region": "us-east-1",
      "versioning": "Enabled",
      "encryption": "aws:kms",
      "tags": {"Environment": "prod"}
    }],
    "glue_databases": [{
      "name": "analytics_catalog",
      "tables_count": 45,
      "location": "s3://my-data-lake/analytics/"
    }]
  },
  "summary": {
    "total_resources": 52,
    "s3_buckets_count": 1,
    "glue_databases_count": 1
  }
}
```

### Cost Estimate Response
```json
{
  "monthly_cost": 245.50,
  "currency": "USD",
  "breakdown": {
    "S3 Storage": 28.75,
    "Athena Queries": 26.00,
    "Glue Crawler": 190.75
  },
  "assumptions": {
    "S3 Storage": "100 GB stored",
    "Athena": "100 queries, 10.0 GB avg scan"
  }
}
```

## 🛠️ Development

### Backend Development

```bash
# Run with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest

# Format code
black app/
```

### Frontend Development

```bash
# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

## 📝 Project Structure

```
dashboard/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── discovery.py
│   │   │       ├── cost.py
│   │   │       ├── deployment.py
│   │   │       ├── monitoring.py
│   │   │       └── config.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── services/
│   │   │   └── aws_service.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔐 Security

- AWS credentials stored securely (environment variables)
- CORS properly configured
- Input validation on all endpoints
- HTTPS required in production
- Rate limiting (to be implemented)

## 🚀 Deployment to Production

### Backend
1. Set production environment variables
2. Use production-grade WSGI server (Gunicorn)
3. Enable HTTPS
4. Configure proper CORS origins
5. Set up monitoring and logging

### Frontend
1. Build production bundle: `npm run build`
2. Serve with Nginx or CDN
3. Configure environment variables
4. Enable HTTPS
5. Set up CDN caching

## 📚 Additional Resources

- [deltalake-aws Documentation](../README.md)
- [Architecture Documentation](../docs/ARCHITECTURE.md)
- [Improvements Documentation](../IMPROVEMENTS.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Material-UI Documentation](https://mui.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Cannot connect to AWS
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify environment variables
echo $AWS_REGION
echo $AWS_ACCESS_KEY_ID
```

**Problem**: Module not found errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install -e ../../  # Install deltalake-aws
```

### Frontend Issues

**Problem**: Cannot connect to API
```bash
# Check API is running
curl http://localhost:8000/api/v1/health

# Verify VITE_API_URL in .env
cat .env
```

**Problem**: Dependencies not installed
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at `/api/docs`
