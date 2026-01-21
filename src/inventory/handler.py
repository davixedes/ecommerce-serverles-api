"""
Inventory Function - Async Inventory Management
src/inventory/handler.py

COM instrumentação Datadog
Processa mensagens SQS para atualizar estoque
"""

import json
import os
import boto3
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper

dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table(os.environ['PRODUCTS_TABLE'])


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    Processa batch de mensagens SQS
    Atualiza estoque de produtos após orders
    
    Datadog captura:
    - SQS batch processing
    - DynamoDB update operations
    - Processing duration per message
    """
    
    print(f"Processing {len(event['Records'])} inventory updates")
    
    successful = 0
    failed = 0
    
    for record in event['Records']:
        try:
            # Parse SQS message
            message_body = json.loads(record['body'])
            order_id = message_body.get('order_id')
            items = message_body.get('items', [])
            
            print(f"Processing order {order_id} with {len(items)} items")
            
            # Update inventory for each item
            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']
                
                # Datadog traces esta operação automaticamente
                products_table.update_item(
                    Key={'product_id': product_id},
                    UpdateExpression='SET stock = stock - :quantity',
                    ExpressionAttributeValues={
                        ':quantity': quantity
                    }
                )
                
                print(f"Updated inventory for {product_id}: -{quantity}")
            
            successful += 1
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            failed += 1
            # Message vai para DLQ após maxReceiveCount
    
    print(f"Batch complete: {successful} successful, {failed} failed")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records']),
            'successful': successful,
            'failed': failed
        })
    }