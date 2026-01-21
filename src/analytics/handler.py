"""
Analytics Function - Order Analytics Processing
src/analytics/handler.py

COM instrumentação Datadog
Processa eventos SNS para analytics
"""

import json
import os
import boto3
from datetime import datetime
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    Processa eventos de orders do SNS
    Calcula métricas e analytics
    
    SNS → Lambda (este handler)
    
    Datadog captura:
    - SNS event processing
    - DynamoDB queries
    - Analytics calculations
    """
    
    print(f"Processing {len(event['Records'])} analytics events")
    
    for record in event['Records']:
        try:
            # Parse SNS message
            sns_message = json.loads(record['Sns']['Message'])
            
            order_id = sns_message.get('order_id')
            customer_id = sns_message.get('customer_id')
            total_amount = Decimal(str(sns_message.get('total_amount', 0)))
            event_type = sns_message.get('event_type')
            
            print(f"Analytics event: {event_type} - Order {order_id}")
            
            if event_type == 'order_created':
                # Processar analytics do novo order
                process_order_analytics(
                    order_id, 
                    customer_id, 
                    total_amount
                )
            
        except Exception as e:
            print(f"Error processing analytics: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records'])
        })
    }


def process_order_analytics(order_id, customer_id, total_amount):
    """
    Processa analytics do order
    
    Em produção real:
    - Enviaria para data warehouse
    - Atualizaria dashboards
    - Calcularia KPIs
    - Trigger ML models
    """
    
    print(f"Processing analytics for order {order_id}")
    
    # Simular cálculos de analytics
    analytics = {
        'order_id': order_id,
        'customer_id': customer_id,
        'total_amount': float(total_amount),
        'timestamp': datetime.utcnow().isoformat(),
        'metrics': {
            'order_value': float(total_amount),
            'currency': 'USD',
            'channel': 'web'
        }
    }
    
    # Em produção:
    # - Enviar para Kinesis Data Firehose
    # - Escrever em S3 para data lake
    # - Atualizar DynamoDB analytics table
    # - Trigger CloudWatch custom metrics
    
    # Datadog traceia qualquer operação AWS automaticamente
    
    print(f"Analytics processed: {analytics}")
    
    # Simular agregações
    calculate_daily_metrics(customer_id, total_amount)
    
    return analytics


def calculate_daily_metrics(customer_id, amount):
    """Calcula métricas diárias agregadas"""
    
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    print(f"Updating daily metrics for {today}")
    print(f"Customer {customer_id} - Amount: ${amount}")
    
    # Em produção:
    # - Atualizar contadores em DynamoDB
    # - Atualizar Redis cache
    # - Enviar custom metrics para CloudWatch
    # - Atualizar Datadog custom metrics
    
    metrics = {
        'date': today,
        'orders_count': 1,
        'revenue': float(amount),
        'customer_id': customer_id
    }
    
    print(f"Daily metrics: {metrics}")
    
    return metrics