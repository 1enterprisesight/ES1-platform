/**
 * Service Template - Node.js
 * Replace SERVICE_NAME with your actual service name.
 */
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const promClient = require('prom-client');

const SERVICE_NAME = 'service-template-node'; // TODO: Replace with actual service name
const PORT = process.env.PORT || 8000;

// Initialize Prometheus metrics
const collectDefaultMetrics = promClient.collectDefaultMetrics;
collectDefaultMetrics();

const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'endpoint', 'status'],
});

const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request latency',
  labelNames: ['method', 'endpoint'],
});

const app = express();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Metrics middleware
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestsTotal.inc({ method: req.method, endpoint: req.path, status: res.statusCode });
    httpRequestDuration.observe({ method: req.method, endpoint: req.path }, duration);
  });
  next();
});

// Health check endpoint (liveness probe)
app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

// Readiness check endpoint (readiness probe)
app.get('/ready', async (req, res) => {
  // TODO: Add dependency checks (database, redis, etc.)
  res.json({ status: 'ready' });
});

// Prometheus metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.send(await promClient.register.metrics());
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: SERVICE_NAME,
    version: '0.1.0',
    status: 'running',
  });
});

// TODO: Add your service-specific routes below

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal Server Error' });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`${SERVICE_NAME} listening on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  process.exit(0);
});
