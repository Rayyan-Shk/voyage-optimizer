# 🚀 GitHub Actions Workflows - Ship Planning System

This directory contains GitHub Actions workflows for continuous integration and deployment of the Ship Planning & Optimization System.

## 📋 Available Workflows

### 1. 🔍 CI - Lint & Test (`ci.yml`)

**Triggers:**

- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

- **🧹 Code Quality**: Runs linting and formatting checks
  - Black (code formatting)
  - isort (import sorting)
  - Flake8 (linting)
  - MyPy (type checking)
- **🧪 Tests**: Runs the test suite with coverage
  - PostgreSQL 15 service
  - Redis 7 service
  - pytest with coverage reporting
  - Codecov integration
- **🔒 Security Scan**: Security analysis
  - Safety (dependency vulnerabilities)
  - Bandit (security linting)

**Caching:**

- pip dependencies cached for faster builds
- Separate cache keys for lint and test jobs

### 2. 🐳 Docker Build & Push (`docker-build.yml`)

**Triggers:**

- Push to `main` or `develop` branches
- Tags matching `v*`
- Pull requests to `main`

**Jobs:**

- **🏗️ Build & Push**: Multi-platform Docker image building
  - Builds for `linux/amd64` and `linux/arm64`
  - Pushes to GitHub Container Registry (`ghcr.io`)
  - Smart tagging based on branch/tag/PR
  - Docker layer caching for faster builds
- **🔒 Security Scan**: Container vulnerability scanning
  - Trivy security scanner
  - SARIF results uploaded to GitHub Security
- **🏗️ Multi-Architecture Test**: Tests images on different platforms

**Features:**

- Multi-platform builds (AMD64 + ARM64)
- Smart image tagging
- Security scanning with Trivy
- Docker layer caching
- Only pushes on non-PR events

### 3. 🚀 Deploy to Staging (`deploy-staging.yml`)

**Triggers:**

- Push to `develop` branch
- Manual workflow dispatch with options

**Jobs:**

- **🔧 Prepare**: Sets up deployment configuration
- **🏠 Deploy Local**: Deploys to local staging environment
  - Uses Docker Compose with staging overrides
  - Creates staging-specific environment
  - Runs health checks
- **☁️ Deploy Cloud**: Placeholder for cloud deployment
  - Ready for AWS/GCP/Azure integration
- **🔄 Rollback**: Automatic rollback on failure
- **🧹 Cleanup**: Resource cleanup

**Environments:**

- `staging`: Default local staging
- `staging-local`: Explicit local staging
- `staging-cloud`: Cloud staging deployment

## 🔧 Setup Instructions

### 1. Repository Secrets

Add these secrets to your GitHub repository:

```bash
# Required secrets
WEATHER_API_KEY=your_openweather_api_key
SECRET_KEY=your-super-secret-key-for-production

# Optional for cloud deployment
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
GCP_SERVICE_ACCOUNT_KEY=your_gcp_service_account_json
AZURE_CREDENTIALS=your_azure_service_principal_json
```

### 2. Enable GitHub Packages

1. Go to your repository settings
2. Navigate to "Actions" → "General"
3. Under "Workflow permissions", select "Read and write permissions"
4. Check "Allow GitHub Actions to create and approve pull requests"

### 3. Environment Protection Rules

Set up environment protection rules for staging:

1. Go to Settings → Environments
2. Create environments: `staging`, `staging-local`, `staging-cloud`
3. Add protection rules as needed
4. Add environment-specific secrets

## 📊 Workflow Optimization Features

### Caching Strategy

- **pip dependencies**: Cached by `requirements.txt` hash
- **Docker layers**: GitHub Actions cache for faster builds
- **Separate cache keys**: Different keys for lint vs test jobs

### Parallel Execution

- **Lint job**: All linting tools run in parallel steps
- **Multi-platform builds**: ARM64 and AMD64 builds run in parallel
- **Test services**: PostgreSQL and Redis start in parallel

### Smart Triggering

- **PR builds**: Only run CI, no deployment
- **Branch builds**: Full CI + deployment pipeline
- **Tag builds**: Release builds with proper versioning

## 🔍 Monitoring & Debugging

### Viewing Workflow Runs

1. Go to the "Actions" tab in your repository
2. Select the workflow you want to view
3. Click on a specific run to see details

### Common Issues & Solutions

#### 1. **Test Failures**

```bash
# Check test logs in the "🧪 Tests" job
# Common issues:
# - Database connection problems
# - Missing environment variables
# - Test data setup issues
```

#### 2. **Docker Build Failures**

```bash
# Check build logs in the "🏗️ Build & Push" job
# Common issues:
# - Dockerfile syntax errors
# - Missing dependencies
# - Registry authentication problems
```

#### 3. **Deployment Failures**

```bash
# Check deployment logs in the "🏠 Deploy Local" job
# Common issues:
# - Port conflicts
# - Environment variable problems
# - Service startup failures
```

### Debug Mode

Enable debug logging by setting repository variable:

```bash
ACTIONS_STEP_DEBUG=true
```

## 🚀 Usage Examples

### Manual Staging Deployment

```bash
# Go to Actions → Deploy to Staging → Run workflow
# Select options:
# - Environment: staging-local
# - Deploy Type: docker-compose
```

### Triggering Builds

```bash
# Push to develop (triggers staging deployment)
git push origin develop

# Push to main (triggers production-ready build)
git push origin main

# Create release tag (triggers versioned build)
git tag v1.0.0
git push origin v1.0.0
```

## 🔮 Future Enhancements

### Planned Features

- [ ] Production deployment workflow
- [ ] Blue-green deployment strategy
- [ ] Kubernetes deployment support
- [ ] Performance testing integration
- [ ] Slack/Teams notifications
- [ ] Automated rollback triggers
- [ ] Multi-region deployment
- [ ] Load testing integration

### Cloud Provider Integration

- [ ] AWS ECS deployment
- [ ] Google Cloud Run deployment
- [ ] Azure Container Instances
- [ ] Kubernetes (EKS/GKE/AKS)

## 📞 Support

For workflow issues:

1. Check the workflow run logs
2. Review this documentation
3. Check repository secrets and environment variables
4. Create an issue with workflow run details

---

**Happy Deploying! 🚢**
