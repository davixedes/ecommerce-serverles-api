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
import random
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


# Simula imports pesados (pandas, numpy, ML models, etc.)
time.sleep(0.5)
time.sleep(0.5)
time.sleep(0.5)
time.sleep(0.5)
time.sleep(0.5)
time.sleep(0.5)

COLD_START_TIME = time.time()
IS_COLD_START = True


class DecimalEncoder(json.JSONEncoder):
    """Helper para serializar Decimal"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """Handler principal - Order Management"""
    global IS_COLD_START

    http_method = event['requestContext']['http']['method']
    path = event['rawPath']

    # Detectar se é cold start
    time_since_init = time.time() - COLD_START_TIME
    is_cold = IS_COLD_START or time_since_init < 5

    if is_cold:
        IS_COLD_START = False

    try:
        # POST /orders - Create new order
        if http_method == 'POST' and path == '/orders':
            return create_order(event, context, is_cold)

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


def create_order(event, context, is_cold_start=False):
    """Cria novo pedido e processa pagamento"""
    
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
    
    print(f"Validating products... Total: ${total_amount}")

    # 2. Processar pagamento
    print("Processing payment...")
    payment_start = time.time()

    # Determinar URL da payment API
    if is_cold_start:
        payment_url = "https://httpbin.org/delay/3.5"
    else:
        is_intermittent_failure = random.random() < 0.15
        if is_intermittent_failure:
            payment_url = "https://httpbin.org/delay/6"
        else:
            delay = random.uniform(0.8, 1.5)
            payment_url = f"https://httpbin.org/delay/{delay:.1f}"

    try:
        payment_response = requests.post(
            payment_url,
            json={
                'customer_id': customer_id,
                'amount': float(total_amount),
                'currency': 'USD'
            },
            timeout=10  # Timeout do requests (não da Lambda)
        )

        payment_time = time.time() - payment_start
        print(f"Payment completed in {payment_time:.2f}s")

        if payment_response.status_code != 200:
            return {
                'statusCode': 502,
                'body': json.dumps({'error': 'Payment gateway error'})
            }

        payment_data = payment_response.json()

    except requests.Timeout:
        print("ERROR: Payment gateway timeout")
        return {
            'statusCode': 504,
            'body': json.dumps({'error': 'Payment gateway timeout'})
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 502,
            'body': json.dumps({'error': 'Payment processing failed'})
        }

    # 3. Salvar order no DynamoDB
    
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

    # 4. Publicar evento no SNS
    
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

    # 5. Enviar mensagem para fila de inventário
    sqs.send_message(
        QueueUrl=INVENTORY_QUEUE_URL,
        MessageBody=json.dumps({
            'order_id': order_id,
            'items': validated_items
        }, cls=DecimalEncoder)
    )

    print(f"Order {order_id} created successfully")
    
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