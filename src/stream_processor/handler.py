"""
DynamoDB Stream Processor
src/stream_processor/handler.py

COM instrumentação Datadog
Processa mudanças no OrdersTable via DynamoDB Streams
"""

import json
import os
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    Processa DynamoDB Stream events
    Reage a mudanças na tabela Orders
    
    DynamoDB Table → Streams → Lambda (este handler)
    
    Datadog captura:
    - Stream record processing
    - Event types (INSERT, MODIFY, REMOVE)
    - Processing duration per record
    - Batch size and timing
    """
    
    print(f"Processing {len(event['Records'])} DynamoDB stream records")
    
    inserts = 0
    modifies = 0
    removes = 0
    
    for record in event['Records']:
        try:
            event_name = record['eventName']
            
            if event_name == 'INSERT':
                inserts += 1
                handle_new_order(record)
            
            elif event_name == 'MODIFY':
                modifies += 1
                handle_order_update(record)
            
            elif event_name == 'REMOVE':
                removes += 1
                handle_order_deletion(record)
            
        except Exception as e:
            print(f"Error processing stream record: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"Stream processing complete: {inserts} inserts, {modifies} modifies, {removes} removes")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records']),
            'inserts': inserts,
            'modifies': modifies,
            'removes': removes
        })
    }


def handle_new_order(record):
    """
    Processa novo order inserido
    
    Event Type: INSERT
    Contém: NewImage (dados do order)
    """
    
    new_image = record['dynamodb']['NewImage']
    order_id = new_image['order_id']['S']
    customer_id = new_image['customer_id']['S']
    
    print(f"New order detected: {order_id}")
    
    # Extrair dados do order
    order_data = parse_dynamodb_item(new_image)
    
    print(f"Order details: {json.dumps(order_data, cls=DecimalEncoder)}")
    
    # Em produção:
    # - Enviar para data warehouse
    # - Atualizar cache
    # - Trigger workflows adicionais
    # - Notificar sistemas externos
    
    # Exemplo: atualizar cache de customer orders
    update_customer_cache(customer_id, order_id)
    
    return order_data


def handle_order_update(record):
    """
    Processa atualização de order existente
    
    Event Type: MODIFY
    Contém: OldImage e NewImage
    """
    
    old_image = record['dynamodb']['OldImage']
    new_image = record['dynamodb']['NewImage']
    
    order_id = new_image['order_id']['S']
    
    print(f"Order updated: {order_id}")
    
    # Comparar old vs new para ver o que mudou
    old_status = old_image.get('status', {}).get('S', 'unknown')
    new_status = new_image.get('status', {}).get('S', 'unknown')
    
    if old_status != new_status:
        print(f"Status changed: {old_status} → {new_status}")
        
        # Em produção:
        # - Log mudanças de status
        # - Trigger notificações
        # - Atualizar analytics
        
        if new_status == 'shipped':
            handle_order_shipped(order_id)
        
        elif new_status == 'cancelled':
            handle_order_cancelled(order_id)
    
    # Verificar mudanças em fraud_score
    old_fraud_score = old_image.get('fraud_score')
    new_fraud_score = new_image.get('fraud_score')
    
    if new_fraud_score and old_fraud_score != new_fraud_score:
        score = float(new_fraud_score['N'])
        print(f"Fraud score updated: {score:.2f}")
        
        if score >= 0.7:
            print(f"⚠️ High risk order detected: {order_id}")
            # Trigger review workflow


def handle_order_deletion(record):
    """
    Processa deleção de order
    
    Event Type: REMOVE
    Contém: OldImage (dados antes da deleção)
    """
    
    old_image = record['dynamodb']['OldImage']
    order_id = old_image['order_id']['S']
    
    print(f"Order deleted: {order_id}")
    
    # Em produção:
    # - Arquivar dados
    # - Limpar caches
    # - Audit log
    # - Notificar sistemas que dependem deste order


def parse_dynamodb_item(item):
    """
    Converte DynamoDB item format para Python dict
    
    DynamoDB format:
    {'field': {'S': 'value'}} ou {'field': {'N': '123'}}
    
    Python dict:
    {'field': 'value'} ou {'field': 123}
    """
    
    result = {}
    
    for key, value in item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = Decimal(value['N'])
        elif 'BOOL' in value:
            result[key] = value['BOOL']
        elif 'M' in value:
            result[key] = parse_dynamodb_item(value['M'])
        elif 'L' in value:
            result[key] = [parse_dynamodb_item({'item': v})['item'] for v in value['L']]
    
    return result


def update_customer_cache(customer_id, order_id):
    """
    Atualiza cache de orders do customer
    
    Em produção:
    - Atualizar ElastiCache/Redis
    - Invalidar CDN cache
    - Atualizar materialização
    """
    
    print(f"Updating cache for customer {customer_id}: added order {order_id}")
    
    # Simular update de cache
    # redis.lpush(f"customer:{customer_id}:orders", order_id)


def handle_order_shipped(order_id):
    """Processa order que foi shipped"""
    
    print(f"Order shipped: {order_id}")
    
    # Em produção:
    # - Enviar email de tracking
    # - Atualizar delivery estimatives
    # - Notificar warehouse


def handle_order_cancelled(order_id):
    """Processa order cancelado"""
    
    print(f"Order cancelled: {order_id}")
    
    # Em produção:
    # - Reverter inventory
    # - Processar refund
    # - Notificar customer
    # - Atualizar analytics