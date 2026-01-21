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


# ⚠️ Simulando módulos pesados que causam cold start lento
# Em aplicações reais: pandas, numpy, ML models, etc.
# Cada import adiciona ~500ms ao cold start
print("🥶 COLD START DETECTED - Loading heavy modules...")
print("Loading heavy module 1 (pandas)...")
time.sleep(0.5)
print("Loading heavy module 2 (numpy)...")
time.sleep(0.5)
print("Loading heavy module 3 (ML models)...")
time.sleep(0.5)
print("Loading heavy module 4 (boto3 extras)...")
time.sleep(0.5)
print("Loading heavy module 5 (connection pools)...")
time.sleep(0.5)
print("Loading heavy module 6 (config/secrets)...")
time.sleep(0.5)

# Total: ~3 segundos de cold start!
COLD_START_TIME = time.time()
print(f"✅ All modules loaded - ready to process requests (Cold start: ~3s)")

# Flag para rastrear se é cold start
IS_COLD_START = True


class DecimalEncoder(json.JSONEncoder):
    """Helper para serializar Decimal"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Handler principal - Order Management

    COMPORTAMENTO ESPERADO:
    - Cold start: SEMPRE falha com timeout/502 (Cold start 3s + Payment 3s = 6s > 5s timeout)
    - Warm start: 85% sucesso, 15% falha esporádica (simula problemas intermitentes)

    Isso gera ~15% de falha geral, mas concentrado em cold starts.
    """
    global IS_COLD_START

    http_method = event['requestContext']['http']['method']
    path = event['rawPath']

    # Detectar se é cold start (primeira execução após carregar módulos)
    time_since_init = time.time() - COLD_START_TIME
    is_cold = IS_COLD_START or time_since_init < 5  # Primeiros 5s após init

    if is_cold:
        print(f"🥶 COLD START REQUEST (time since init: {time_since_init:.2f}s)")
        IS_COLD_START = False  # Próximas serão warm
    else:
        print(f"🔥 WARM START REQUEST")

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
    """
    Cria novo pedido e processa pagamento

    COMPORTAMENTO:
    - Cold start: Payment API demora 3.5s + cold start 3s = 6.5s → TIMEOUT (limite 5s)
    - Warm start: Payment API demora 0.8-1.5s, mas 15% das vezes demora 6s (timeout)

    FLUXO:
    1. Validar produtos no DynamoDB (~100ms)
    2. Chamar Payment API (varia conforme cold/warm)
    3. Salvar order no DynamoDB (~100ms)
    4. Publicar evento SNS (~50ms)
    5. Enviar mensagem SQS (~50ms)
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

    payment_start = time.time()

    # ⚠️ LÓGICA DO PROBLEMA:
    # - Cold start: Payment API sempre lento (3.5s) → Com cold start total = 6.5s → TIMEOUT!
    # - Warm start: 85% rápido (0.8-1.5s), 15% lento (6s) → Falha esporádica

    if is_cold_start:
        # Cold start: SEMPRE usa API lenta (httpbin.org/delay/3.5)
        # Total: cold start 3s + payment 3.5s = 6.5s > 5s timeout = FALHA
        payment_url = "https://httpbin.org/delay/3.5"
        print(f"🥶 COLD START: Using SLOW payment API (will timeout!)")
        print(f"   Expected: 3.5s payment + 3s cold start = 6.5s > 5s timeout")
    else:
        # Warm start: 15% de chance de usar API lenta (intermitente)
        is_intermittent_failure = random.random() < 0.15

        if is_intermittent_failure:
            # 15% das vezes: API lenta causa timeout
            payment_url = "https://httpbin.org/delay/6"
            print(f"⚠️ INTERMITTENT FAILURE: Using slow payment API (will timeout)")
            print(f"   This is the 15% failure case")
        else:
            # 85% das vezes: API rápida, sucesso
            delay = random.uniform(0.8, 1.5)
            payment_url = f"https://httpbin.org/delay/{delay:.1f}"
            print(f"🔥 WARM START: Using fast payment API (~{delay:.1f}s)")

    print(f"Calling: {payment_url}")

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
        print(f"Payment processed in {payment_time:.3f}s")

        if payment_response.status_code != 200:
            print(f"Payment failed: {payment_response.status_code}")
            return {
                'statusCode': 502,
                'body': json.dumps({'error': 'Payment gateway error'})
            }

        payment_data = payment_response.json()
        print(f"Payment successful: {payment_data}")

    except requests.Timeout:
        print("❌ Payment API timeout!")
        return {
            'statusCode': 504,
            'body': json.dumps({'error': 'Payment gateway timeout'})
        }

    except Exception as e:
        print(f"❌ Payment error: {str(e)}")
        return {
            'statusCode': 502,
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