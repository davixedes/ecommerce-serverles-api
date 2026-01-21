"""
Email Function - Async Email Notifications
src/email/handler.py

COM instrumentação Datadog
Consome mensagens do SNS via SQS e envia emails
"""

import json
import os
import boto3
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    Processa batch de notificações de email via SQS
    
    SNS → SQS → Lambda (este handler)
    
    Datadog captura:
    - SQS batch processing
    - SNS message correlation
    - DynamoDB lookups
    - Email sending simulation
    """
    
    print(f"Processing {len(event['Records'])} email notifications")
    
    for record in event['Records']:
        try:
            # Parse SQS message (que veio do SNS)
            message_body = json.loads(record['body'])
            
            # SNS wraps a mensagem
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
            else:
                sns_message = message_body
            
            order_id = sns_message.get('order_id')
            customer_id = sns_message.get('customer_id')
            event_type = sns_message.get('event_type')
            
            print(f"Email event: {event_type} for order {order_id}")
            
            # Buscar detalhes do order
            # Datadog traces esta query automaticamente
            response = orders_table.get_item(
                Key={
                    'order_id': order_id,
                    'timestamp': sns_message.get('timestamp', 0)
                }
            )
            
            if 'Item' not in response:
                print(f"Order {order_id} not found")
                continue
            
            order = response['Item']
            
            # Simular envio de email
            # Em produção: usar SES, SendGrid, etc
            email_content = generate_email(event_type, order, customer_id)
            
            # Aqui você chamaria seu email service
            # ses.send_email(...) ou requests.post(sendgrid_api)
            # Datadog traceria essa chamada automaticamente
            
            print(f"Email sent to customer {customer_id}")
            print(f"Subject: {email_content['subject']}")
            
        except Exception as e:
            print(f"Error processing email: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records'])
        })
    }


def generate_email(event_type, order, customer_id):
    """Gera conteúdo do email baseado no event type"""
    
    from_email = os.environ.get('FROM_EMAIL', 'noreply@ecommerce-demo.com')
    
    if event_type == 'order_created':
        return {
            'to': f'{customer_id}@example.com',
            'from': from_email,
            'subject': f'Order Confirmation - {order["order_id"]}',
            'body': f'''
                Thank you for your order!
                
                Order ID: {order["order_id"]}
                Total: ${order["total_amount"]}
                Status: {order["status"]}
                
                We'll send you a shipping notification soon.
            '''
        }
    
    elif event_type == 'order_confirmed':
        return {
            'to': f'{customer_id}@example.com',
            'from': from_email,
            'subject': f'Payment Confirmed - {order["order_id"]}',
            'body': f'''
                Your payment has been confirmed!
                
                Order ID: {order["order_id"]}
                Total: ${order["total_amount"]}
                
                Your order is being prepared for shipping.
            '''
        }
    
    elif event_type == 'order_shipped':
        return {
            'to': f'{customer_id}@example.com',
            'from': from_email,
            'subject': f'Order Shipped - {order["order_id"]}',
            'body': f'''
                Your order has been shipped!
                
                Order ID: {order["order_id"]}
                Tracking: TRACK-12345
                
                Expected delivery: 3-5 business days
            '''
        }
    
    else:
        return {
            'to': f'{customer_id}@example.com',
            'from': from_email,
            'subject': f'Order Update - {order["order_id"]}',
            'body': f'Order {order["order_id"]} - Status: {event_type}'
        }