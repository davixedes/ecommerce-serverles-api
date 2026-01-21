# Serverless E-Commerce API

A serverless e-commerce application built with AWS SAM (Serverless Application Model), demonstrating event-driven architecture patterns with Lambda, DynamoDB, SNS, and SQS.

## Architecture

This project demonstrates a production-ready serverless architecture with:

- **API Gateway HTTP API** - REST API endpoints
- **AWS Lambda** - Serverless compute for business logic
- **DynamoDB** - NoSQL database with streams
- **SNS (Simple Notification Service)** - Event publishing
- **SQS (Simple Queue Service)** - Asynchronous message processing
- **Event-Driven Architecture** - Decoupled services communicating via events

## Services

### 1. Products Service
- **GET /products** - List all products
- **GET /products/{id}** - Get product details
- **Technology**: Lambda + DynamoDB
- **Features**: Fast read operations with DynamoDB GetItem/Scan

### 2. Orders Service
- **POST /orders** - Create new order
- **GET /orders** - List orders
- **Technology**: Lambda + DynamoDB + SNS + SQS
- **Features**:
  - Order creation with payment processing
  - Event publishing to SNS topics
  - Async inventory management via SQS

### 3. Inventory Service (Async)
- Processes inventory updates from SQS queue
- Triggered by order events
- Reserved concurrency for rate limiting

### 4. Email Service (Async)
- Sends order confirmation emails
- Subscribes to order events via SNS
- Batch processing from SQS

### 5. Analytics Service (Async)
- Tracks order metrics
- Direct SNS subscription with message filtering
- Real-time analytics processing

### 6. Fraud Detection Service (Async)
- Analyzes payment transactions for fraud
- High memory allocation for ML models
- Processes from dedicated fraud queue

### 7. Stream Processor
- Processes DynamoDB Stream events
- Reacts to order table changes
- Handles INSERT, MODIFY, REMOVE events

## Project Structure

```
.
├── src/
│   ├── products/          # Products API Lambda
│   ├── orders/            # Orders API Lambda
│   ├── inventory/         # Inventory processor Lambda
│   ├── email/             # Email notifications Lambda
│   ├── analytics/         # Analytics Lambda
│   ├── fraud/             # Fraud detection Lambda
│   └── stream_processor/  # DynamoDB Streams processor
├── tests/
│   └── test_script.py     # Load testing script
├── template.yaml          # SAM template (Infrastructure as Code)
└── README.md
```

## Prerequisites

- AWS CLI configured with credentials
- AWS SAM CLI installed
- Python 3.11+
- An AWS account

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd serverless-project
```

2. Install Python dependencies (for local testing):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Deployment

1. Build the application:
```bash
sam build
```

2. Deploy to AWS:
```bash
sam deploy --guided
```

Follow the prompts to configure:
- Stack name
- AWS Region
- Confirm changes before deploy
- Allow SAM CLI IAM role creation
- Save arguments to configuration file

3. Get the API endpoint:
```bash
sam list stack-outputs --stack-name <your-stack-name>
```

## Testing

### Load Testing

Run the load test script to test all endpoints:

```bash
cd tests
python test_script.py <API_URL> [requests_per_endpoint]
```

Example:
```bash
python test_script.py https://abc123.execute-api.us-east-1.amazonaws.com 100
```

This will test:
- GET /products (expected: fast, 100% success)
- GET /products/{id} (expected: fast, 100% success)
- POST /orders (demonstrates cold start + timeout issues)

### Manual Testing

Test products endpoint:
```bash
curl https://<your-api-url>/products
```

Create an order:
```bash
curl -X POST https://<your-api-url>/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer-123",
    "items": [
      {"product_id": "prod-001", "quantity": 2}
    ]
  }'
```

## Architecture Highlights

### Event-Driven Pattern
```
Orders Lambda → SNS Topic → Multiple Subscribers
                  ├─→ Email Queue → Email Lambda
                  ├─→ Analytics Lambda (direct)
                  └─→ Fraud Queue → Fraud Lambda
```

### DynamoDB Streams
```
Orders Table → DynamoDB Streams → Stream Processor Lambda
```

### Message Filtering
- Email service only receives `order_confirmed` and `order_shipped` events
- Analytics service only receives `order_created` events
- Reduces unnecessary Lambda invocations

## Performance Characteristics

### Products Service
- **Latency**: ~50-200ms
- **Cold Start**: ~500ms
- **Throughput**: High (DynamoDB auto-scaling)

### Orders Service (Intentionally Slow)
- **Latency**: ~6+ seconds (payment API delay)
- **Cold Start**: ~3 seconds (heavy dependencies)
- **Memory**: 128MB (causes frequent cold starts)
- **Timeout**: 5 seconds (causes failures)

Note: The Orders service is intentionally configured with performance issues to demonstrate monitoring and optimization needs.

## Monitoring

This application includes infrastructure for observability:
- CloudWatch Logs for all Lambda functions
- DynamoDB metrics (read/write capacity, throttling)
- SQS metrics (messages in queue, processing time)
- SNS metrics (messages published, delivery rate)

## Resource Cleanup

To delete all AWS resources:
```bash
sam delete --stack-name <your-stack-name>
```

This will remove:
- All Lambda functions
- API Gateway
- DynamoDB tables
- SNS topics
- SQS queues
- IAM roles and policies

## Cost Optimization

This architecture uses serverless pricing:
- **Lambda**: Pay per request + execution time
- **DynamoDB**: On-demand billing (pay per request)
- **API Gateway**: Pay per API call
- **SNS/SQS**: Pay per message

Expected costs for development/testing: < $5/month

## Contributing

Feel free to submit issues and pull requests!

## License

MIT License - see LICENSE file for details

## Related Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [Event-Driven Architecture](https://aws.amazon.com/event-driven-architecture/)
