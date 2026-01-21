"""
Orders Function - E-commerce Order Processing
src/orders/handler.py

SEM instrumentação Datadog - apenas CloudWatch logs
"""

import json
import os
import uuid
import time
import boto3
import requests
from decimal import Decimal
from datetime import datetime

# AWS Clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
sns = boto3.client('sns')

# Environment Variables
ORDERS_TABLE = os.environ['ORDERS_TABLE']
PRODUCTS_TABLE = os.environ['PRODUCTS_TABLE']
INVENTORY_QUEUE_URL = os.environ['INVENTORY_QUEUE_URL']
ORDER_EVENTS_TOPIC_ARN = os.environ['ORDER_EVENTS_TOPIC_ARN']
PAYMENT_EVENTS_TOPIC_ARN = os.environ['PAYMENT_EVENTS_TOPIC_ARN']
PAYMENT_API_URL = os.environ['PAYMENT_API_URL']

orders_table = dynamodb.Table(ORDERS_TABLE)
products_table = dynamodb.Table(PRODUCTS_TABLE)


# ⚠️ Simulando módulos pesados que causam cold start lento
# Em aplicações reais: pandas, numpy, ML models, etc.
# Cada import adiciona ~500ms ao cold start
print("Loading heavy module 1...")
time.sleep(0.5)  # Simula import pandas
print("Loading heavy module 2...")
time.sleep(0.5)  # Simula import numpy
print("Loading heavy module 3...")
time.sleep(0.5)  # Simula ML model load
print("Loading heavy module 4...")
time.sleep(0.5)  # Simula other dependencies
print("Loading heavy module 5...")
time.sleep(0.5)  # Simula connection pools
print("Loading heavy module 6...")
time.sleep(0.5)  # Simula configuration load

# Total: ~3 segundos de cold start!
print("All modules loaded - ready to process requests")


class DecimalEncoder(json.JSONEncoder):
    """Helper para serializar Decimal"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Handler principal - Order Management
    
    PROBLEMA:
    - Cold start: ~3 segundos (imports pesados)
    - Payment API: 6 segundos
    - Total em cold start: 9 segundos
    - Timeout configurado: 5 segundos
    - Resultado: TIMEOUT em cold starts!
    
    Warm start funciona:
    - Sem cold start: 0s
    - Payment API: 6 segundos... ⚠️ ainda timeout!
    
    WAIT, na verdade SEMPRE dá timeout porque Payment API > 5s!
    Mas em cold start é ainda PIOR.
    """
    
    http_method = event['requestContext']['http']['method']
    path = event['rawPath']
    
    try:
        # POST /orders - Create new order
        if http_method == 'POST' and path == '/orders':
            return create_order(event, context)
        
        # GET /orders - List orders
        elif http_method == 'GET' and path == '/orders':
            return list_orders(event)
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid request'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


def create_order(event, context):
    """
    Cria novo pedido e processa pagamento
    
    FLUXO:
    1. Validar produtos no DynamoDB (~100ms)
    2. Chamar Payment API (~6000ms) ⚠️ BOTTLENECK
    3. Salvar order no DynamoDB (~100ms)
    4. Publicar evento SNS (~50ms)
    5. Enviar mensagem SQS (~50ms)
    
    Total (warm): ~6.3s → TIMEOUT (limite 5s)!
    Total (cold): ~9.3s → TIMEOUT AINDA PIOR!
    """
    
    # Parse request body
    body = json.loads(event.get('body', '{}'))
    customer_id = body.get('customer_id')
    items = body.get('items', [])
    
    if not customer_id or not items:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing customer_id or items'})
        }
    
    print(f"Customer: {customer_id}, Items: {len(items)}")
    
    # 1. Validar produtos no DynamoDB
    print("Step 1: Validating products...")
    start = time.time()
    
    total_amount = Decimal('0')
    validated_items = []
    
    for item in items:
        product_id = item['product_id']
        quantity = item['quantity']
        
        # Query DynamoDB
        response = products_table.get_item(Key={'product_id': product_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f'Product {product_id} not found'})
            }
        
        product = response['Item']
        price = product['price']
        
        validated_items.append({
            'product_id': product_id,
            'quantity': quantity,
            'price': price,
            'subtotal': price * quantity
        })
        
        total_amount += price * quantity
    
    validation_time = time.time() - start
    print(f"Products validated in {validation_time:.3f}s - Total: ${total_amount}")
    
    # 2. Processar pagamento (BOTTLENECK!)
    print("Step 2: Processing payment...")
    print(f"Calling payment API: {PAYMENT_API_URL}")
    
    payment_start = time.time()
    
    try:
        # ⚠️ Esta chamada demora 6 segundos!
        # Com cold start de 3s, total = 9s
        # Timeout é 5s, então sempre falha!
        payment_response = requests.post(
            PAYMENT_API_URL,
            json={
                'customer_id': customer_id,
                'amount': float(total_amount),
                'currency': 'USD'
            },
            timeout=10  # Timeout do requests, não da Lambda
        )
        
        payment_time = time.time() - payment_start
        print(f"Payment processed in {payment_time:.3f}s")
        
        if payment_response.status_code != 200:
            print(f"Payment failed: {payment_response.status_code}")
            return {
                'statusCode': 402,
                'body': json.dumps({'error': 'Payment failed'})
            }
        
        payment_data = payment_response.json()
        print(f"Payment successful: {payment_data}")
    
    except requests.Timeout:
        print("Payment API timeout!")
        return {
            'statusCode': 504,
            'body': json.dumps({'error': 'Payment gateway timeout'})
        }
    
    except Exception as e:
        print(f"Payment error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Payment processing failed'})
        }
    
    # 3. Salvar order no DynamoDB
    print("Step 3: Saving order to DynamoDB...")
    
    order_id = str(uuid.uuid4())
    timestamp = int(time.time() * 1000)
    
    order = {
        'order_id': order_id,
        'customer_id': customer_id,
        'timestamp': timestamp,
        'items': validated_items,
        'total_amount': total_amount,
        'status': 'confirmed',
        'payment_id': payment_data.get('id', 'unknown'),
        'created_at': datetime.utcnow().isoformat()
    }
    
    orders_table.put_item(Item=order)
    print(f"Order saved: {order_id}")
    
    # 4. Publicar evento no SNS
    print("Step 4: Publishing to SNS...")
    
    sns.publish(
        TopicArn=ORDER_EVENTS_TOPIC_ARN,
        Message=json.dumps({
            'order_id': order_id,
            'customer_id': customer_id,
            'total_amount': float(total_amount),
            'event_type': 'order_created'
        }),
        MessageAttributes={
            'event_type': {
                'DataType': 'String',
                'StringValue': 'order_created'
            }
        }
    )
    
    print("Event published to SNS")
    
    # 5. Enviar mensagem para fila de inventário
    print("Step 5: Sending message to SQS...")
    
    sqs.send_message(
        QueueUrl=INVENTORY_QUEUE_URL,
        MessageBody=json.dumps({
            'order_id': order_id,
            'items': validated_items
        })
    )
    
    print("Message sent to inventory queue")
    print(f"Order processing completed: {order_id}")
    
    return {
        'statusCode': 201,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'order_id': order_id,
            'status': 'confirmed',
            'total_amount': float(total_amount)
        }, cls=DecimalEncoder)
    }


def list_orders(event):
    """Lista orders de um customer"""
    
    query_params = event.get('queryStringParameters') or {}
    customer_id = query_params.get('customer_id')
    
    if not customer_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'customer_id required'})
        }
    
    print(f"Listing orders for customer: {customer_id}")
    
    # Query usando GSI
    response = orders_table.query(
        IndexName='CustomerIndex',
        KeyConditionExpression='customer_id = :customer_id',
        ExpressionAttributeValues={
            ':customer_id': customer_id
        },
        ScanIndexForward=False,  # Mais recentes primeiro
        Limit=20
    )
    
    orders = response.get('Items', [])
    print(f"Found {len(orders)} orders")
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'orders': orders,
            'count': len(orders)
        }, cls=DecimalEncoder)
    }