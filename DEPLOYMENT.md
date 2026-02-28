# ChronosMCP Deployment Guide

## Deployment Options

ChronosMCP can be deployed in three ways:

### 1. MCP Server (Recommended for Hackathon Demo)

**Use Case**: Connect to Claude Desktop, Cursor, or any MCP-compatible client

**Setup**:
```bash
# Start with Docker Compose
docker-compose up -d

# Configure in Claude Desktop
# Edit: ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "chronos-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "chronos-mcp", "python", "-m", "src.main"]
    }
  }
}
```

**Pros**:
- Universal compatibility (works with any MCP client)
- No code changes needed in client applications
- Standard protocol

**Cons**:
- Requires MCP-compatible client

### 2. Hosted Service (Production)

**Use Case**: Deploy as a standalone service with HTTP API

**Setup**:
```bash
# Deploy to cloud (AWS, GCP, Azure)
# Use docker-compose.yml as base

# Add nginx reverse proxy
# Add SSL/TLS certificates
# Configure load balancer
```

**Architecture**:
```
Internet → Load Balancer → ChronosMCP Instances → PostgreSQL (RDS/Cloud SQL)
```

**Pros**:
- Scalable (horizontal scaling)
- High availability
- Centralized management

**Cons**:
- More complex infrastructure
- Higher operational cost

### 3. Embedded Library (Advanced)

**Use Case**: Integrate directly into Python applications

**Setup**:
```python
from src.memory_engine.memory_engine import MemoryEngine
from src.services.embedding_service import EmbeddingService
# ... initialize components

# Use directly in your code
result = await memory_engine.store_with_conflict_resolution(...)
```

**Pros**:
- No network overhead
- Full control
- Custom integrations

**Cons**:
- Requires Python
- More integration work

## Production Checklist

### Security
- [ ] Change JWT_SECRET from default
- [ ] Enable SSL/TLS for database connections
- [ ] Configure firewall rules
- [ ] Set up VPC/network isolation
- [ ] Enable audit logging
- [ ] Implement rate limiting
- [ ] Add API authentication beyond JWT

### Performance
- [ ] Configure connection pooling (adjust DATABASE_POOL_MAX_SIZE)
- [ ] Set up read replicas for PostgreSQL
- [ ] Enable query caching
- [ ] Configure CDN for static assets (if HTTP API)
- [ ] Monitor latency metrics
- [ ] Set up auto-scaling

### Reliability
- [ ] Configure backup strategy (daily snapshots)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerting (PagerDuty/Opsgenie)
- [ ] Test circuit breaker behavior
- [ ] Implement health checks
- [ ] Set up log aggregation (ELK/Datadog)

### Compliance
- [ ] Review data retention policies
- [ ] Implement GDPR compliance (right to deletion)
- [ ] Configure audit log retention
- [ ] Document security measures
- [ ] Perform security audit
- [ ] Set up compliance monitoring

## Environment Variables (Production)

```bash
# Required
OPENAI_API_KEY=sk-prod-key-here
DATABASE_URL=postgresql://user:pass@prod-db:5432/chronos
JWT_SECRET=long-random-secret-min-32-chars

# Performance
DATABASE_POOL_MIN_SIZE=10
DATABASE_POOL_MAX_SIZE=50
RESPONSE_TIMEOUT_MS=200
MAX_CONTEXT_TOKENS=2000

# Security
JWT_ALGORITHM=HS256
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Scaling Strategy

### Vertical Scaling
- Increase PostgreSQL instance size
- Add more CPU/RAM to application containers
- Optimize database indexes

### Horizontal Scaling
- Run multiple ChronosMCP instances behind load balancer
- Use PostgreSQL connection pooler (PgBouncer)
- Implement caching layer (Redis)

### Database Scaling
- Read replicas for query load
- Partitioning for large tables
- Archive old data to cold storage

## Monitoring

### Key Metrics
- Request latency (p50, p95, p99)
- Error rate
- Database connection pool usage
- Memory usage
- CPU usage
- Token consumption (OpenAI API)

### Alerts
- Latency > 200ms for 5 minutes
- Error rate > 1% for 5 minutes
- Database connection pool > 80%
- Circuit breaker opened
- Disk space < 20%

## Backup Strategy

### Database Backups
```bash
# Daily full backup
pg_dump -h localhost -U chronos chronos > backup_$(date +%Y%m%d).sql

# Continuous WAL archiving for point-in-time recovery
```

### Retention Policy
- Daily backups: 30 days
- Weekly backups: 90 days
- Monthly backups: 1 year

## Disaster Recovery

### RTO (Recovery Time Objective): 1 hour
### RPO (Recovery Point Objective): 5 minutes

**Recovery Steps**:
1. Restore PostgreSQL from latest backup
2. Apply WAL logs for point-in-time recovery
3. Start ChronosMCP instances
4. Verify data integrity
5. Resume traffic

## Cost Estimation (AWS Example)

### Small Deployment (Demo/Dev)
- EC2 t3.small (2 vCPU, 2GB RAM): $15/month
- RDS PostgreSQL db.t3.micro: $15/month
- OpenAI API (1M tokens/month): $20/month
- **Total: ~$50/month**

### Medium Deployment (Production)
- EC2 t3.medium x2 (4 vCPU, 4GB RAM): $60/month
- RDS PostgreSQL db.t3.medium: $60/month
- Load Balancer: $20/month
- OpenAI API (10M tokens/month): $200/month
- **Total: ~$340/month**

### Large Deployment (Enterprise)
- EC2 c5.xlarge x4 (16 vCPU, 8GB RAM): $500/month
- RDS PostgreSQL db.r5.xlarge: $300/month
- Load Balancer + Auto Scaling: $50/month
- OpenAI API (100M tokens/month): $2000/month
- **Total: ~$2850/month**

## Troubleshooting

### High Latency
1. Check database connection pool
2. Review slow query log
3. Verify OpenAI API latency
4. Check network latency

### Memory Leaks
1. Monitor container memory usage
2. Check for unclosed database connections
3. Review asyncio task cleanup

### Database Connection Errors
1. Verify connection string
2. Check firewall rules
3. Verify RLS policies
4. Check connection pool limits

## Support

For production support:
- GitHub Issues: <repo-url>/issues
- Email: support@chronos-mcp.example
- Slack: #chronos-mcp-support
