"""
Fraud Detection Function - Fraud Analysis
src/fraud/handler.py

COM instrumentação Datadog
Analisa transações de pagamento para detectar fraude
"""

import json
import os
import boto3
import time
from decimal import Decimal

# ✅ Datadog
#from datadog_lambda.wrapper import datadog_lambda_wrapper

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ['ORDERS_TABLE'])

# Threshold de risco (0-1)
RISK_THRESHOLD = float(os.environ.get('RISK_THRESHOLD', '0.7'))


#@datadog_lambda_wrapper
def lambda_handler(event, context):
    """
    Processa mensagens SQS de payment events
    Análise de fraude em pagamentos
    
    SNS → SQS → Lambda (este handler)
    
    Datadog captura:
    - SQS batch processing
    - ML model inference time (simulado)
    - DynamoDB updates
    - Risk score calculations
    """
    
    print(f"Processing {len(event['Records'])} fraud checks")
    
    high_risk_count = 0
    low_risk_count = 0
    
    for record in event['Records']:
        try:
            # Parse SQS message
            message = json.loads(record['body'])
            
            order_id = message.get('order_id')
            customer_id = message.get('customer_id')
            amount = Decimal(str(message.get('amount', 0)))
            payment_method = message.get('payment_method', 'card')
            
            print(f"Fraud check for order {order_id} - ${amount}")
            
            # Análise de fraude (simulada)
            # Em produção: chamar ML model endpoint (SageMaker)
            risk_score = analyze_fraud_risk(
                customer_id, 
                amount, 
                payment_method
            )
            
            print(f"Risk score: {risk_score:.2f}")
            
            # Classificar risco
            if risk_score >= RISK_THRESHOLD:
                high_risk_count += 1
                handle_high_risk_transaction(order_id, risk_score)
            else:
                low_risk_count += 1
                handle_low_risk_transaction(order_id, risk_score)
            
        except Exception as e:
            print(f"Error in fraud check: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"Fraud check complete: {low_risk_count} low risk, {high_risk_count} high risk")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': len(event['Records']),
            'high_risk': high_risk_count,
            'low_risk': low_risk_count
        })
    }


def analyze_fraud_risk(customer_id, amount, payment_method):
    """
    Análise de risco de fraude
    
    Em produção real:
    - Chamar SageMaker endpoint
    - Análise de padrões históricos
    - Geolocation checks
    - Device fingerprinting
    - Velocity checks
    
    Datadog traceia chamadas a serviços ML automaticamente
    """
    
    print(f"Analyzing fraud risk for customer {customer_id}")
    
    # Simular tempo de inferência do ML model
    # Models reais: 50-500ms
    time.sleep(0.1)  # 100ms
    
    risk_score = 0.0
    
    # Regras simples de exemplo (em produção: ML model)
    
    # 1. Valor alto = mais risco
    if amount > 1000:
        risk_score += 0.3
    elif amount > 500:
        risk_score += 0.2
    
    # 2. Novo customer = mais risco
    # Em produção: query histórico do customer
    if customer_id.startswith('new-'):
        risk_score += 0.4
    
    # 3. Payment method
    if payment_method == 'crypto':
        risk_score += 0.2
    
    # 4. Simular variação aleatória
    import random
    risk_score += random.uniform(-0.1, 0.1)
    
    # Normalizar para 0-1
    risk_score = max(0.0, min(1.0, risk_score))
    
    print(f"Calculated risk score: {risk_score:.2f}")
    
    return risk_score


def handle_high_risk_transaction(order_id, risk_score):
    """
    Processa transação de alto risco
    
    Em produção:
    - Bloquear ordem
    - Notificar equipe de fraude
    - Solicitar verificação adicional
    - Atualizar DynamoDB com flag
    """
    
    print(f"⚠️ HIGH RISK detected for order {order_id}: {risk_score:.2f}")
    
    # Datadog traces esta operação automaticamente
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET fraud_score = :score, fraud_status = :status',
            ExpressionAttributeValues={
                ':score': Decimal(str(risk_score)),
                ':status': 'high_risk_pending_review'
            }
        )
        
        print(f"Order {order_id} marked for review")
        
        # Em produção: enviar alerta
        # sns.publish(AlertTopic, f"High risk order: {order_id}")
        
    except Exception as e:
        print(f"Error updating order: {str(e)}")


def handle_low_risk_transaction(order_id, risk_score):
    """Processa transação de baixo risco"""
    
    print(f"✅ LOW RISK for order {order_id}: {risk_score:.2f}")
    
    # Atualizar order com risk score
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET fraud_score = :score, fraud_status = :status',
            ExpressionAttributeValues={
                ':score': Decimal(str(risk_score)),
                ':status': 'approved'
            }
        )
        
        print(f"Order {order_id} approved")
        
    except Exception as e:
        print(f"Error updating order: {str(e)}")