"""
Products Function - Product Catalog API
src/products/handler.py

COM instrumentação Datadog
"""

import json
import os
import boto3
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['PRODUCTS_TABLE']
products_table = dynamodb.Table(table_name)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    GET /products - List all products
    GET /products/{product_id} - Get specific product
    
    Datadog captura automaticamente:
    - DynamoDB operations
    - Cold starts
    - Latency
    """
    
    http_method = event['requestContext']['http']['method']
    path = event['rawPath']
    
    print(f"Request: {http_method} {path}")
    
    try:
        # GET /products - List all
        if http_method == 'GET' and path == '/products':
            response = products_table.scan(Limit=50)
            products = response.get('Items', [])
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'products': products,
                    'count': len(products)
                }, cls=DecimalEncoder)
            }
        
        # GET /products/{id} - Get specific product
        elif http_method == 'GET' and '/products/' in path:
            product_id = path.split('/')[-1]
            
            response = products_table.get_item(
                Key={'product_id': product_id}
            )
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'Product not found'})
                }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response['Item'], cls=DecimalEncoder)
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Invalid request'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }