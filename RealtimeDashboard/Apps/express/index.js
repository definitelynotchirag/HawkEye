const express = require('express');
const axios = require('axios');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

// OpenTelemetry setup
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-grpc');
const { trace, context } = require('@opentelemetry/api');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');

// Configure OpenTelemetry
const provider = new NodeTracerProvider({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'express-service',
  }),
});

const exporter = new OTLPTraceExporter({
  url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317',
});

provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();

// Register instrumentations for auto-instrumentation
registerInstrumentations({
  instrumentations: [
    new ExpressInstrumentation(),
    new HttpInstrumentation(),
  ],
});

// Create a tracer
const tracer = trace.getTracer('express-service');

// Configure logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'express-service' },
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/express-service.log' }),
  ],
});

const app = express();
const port = process.env.PORT || 3000;
const flaskServiceUrl = process.env.FLASK_SERVICE_URL || 'http://localhost:5000';

app.use(cors());
app.use(express.json());

// Middleware to add tracing context and request ID
app.use((req, res, next) => {
  req.id = uuidv4();
  res.setHeader('X-Request-ID', req.id);
  next();
});

// Log all requests
app.use((req, res, next) => {
  logger.info(`Incoming request`, {
    method: req.method,
    path: req.path,
    requestId: req.id,
    ip: req.ip,
  });
  next();
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.get('/api/data', (req, res) => {
  const span = tracer.startSpan('get-data');
  
  try {
    // Some business logic
    const data = {
      id: uuidv4(),
      name: 'Sample Data',
      timestamp: new Date().toISOString(),
      value: Math.random() * 100,
    };
    
    // Add some attributes to the span
    span.setAttribute('data.id', data.id);
    span.setAttribute('data.value', data.value);
    
    logger.info('Data processed successfully', { 
      requestId: req.id,
      dataId: data.id 
    });
    
    res.json(data);
  } catch (error) {
    span.recordException(error);
    logger.error('Error processing data', { 
      requestId: req.id,
      error: error.message 
    });
    res.status(500).json({ error: error.message });
  } finally {
    span.end();
  }
});

app.get('/api/call-flask', async (req, res) => {
  const span = tracer.startSpan('call-flask-service');
  
  try {
    logger.info('Calling Flask service', { 
      requestId: req.id,
      targetUrl: `${flaskServiceUrl}/health`
    });
    
    const response = await axios.get(`${flaskServiceUrl}/health`);
    
    logger.info('Flask service responded', { 
      requestId: req.id,
      flaskStatus: response.data.status
    });
    
    res.json({ 
      status: 'success',
      flaskData: response.data 
    });
  } catch (error) {
    span.recordException(error);
    logger.error('Error calling Flask service', { 
      requestId: req.id,
      error: error.message 
    });
    res.status(500).json({ 
      status: 'error',
      message: error.message 
    });
  } finally {
    span.end();
  }
});

// Endpoint to forward CloudFront log streams
app.get('/logs/cloudfront', async (req, res) => {
  const span = tracer.startSpan('proxy-cloudfront-logs');
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  
  try {
    // Create a proxy for the Flask log stream
    const axiosResponse = await axios({
      method: 'get',
      url: `${flaskServiceUrl}/logs/cloudfront`,
      responseType: 'stream'
    });
    
    // Pipe the Flask response to our response
    axiosResponse.data.on('data', chunk => {
      res.write(chunk);
    });
    
    // Handle client disconnect
    req.on('close', () => {
      axiosResponse.data.destroy();
      span.end();
      logger.info('Client disconnected from log stream', { requestId: req.id });
    });
    
    // Handle errors
    axiosResponse.data.on('error', err => {
      logger.error('Error in log stream', { 
        requestId: req.id,
        error: err.message 
      });
      span.recordException(err);
      span.end();
      res.end();
    });
  } catch (error) {
    span.recordException(error);
    span.end();
    logger.error('Failed to connect to Flask log stream', { 
      requestId: req.id,
      error: error.message 
    });
    res.status(500).send('Error connecting to log stream');
  }
});

app.listen(port, () => {
  logger.info(`Express service listening at http://localhost:${port}`);
});