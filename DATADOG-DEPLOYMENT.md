# Deployment com Datadog APM

Este guia mostra como fazer deploy da aplicação **COM** instrumentação Datadog para observabilidade completa.

## 📋 Pré-requisitos

1. **Conta Datadog** (trial grátis disponível em [datadoghq.com](https://www.datadoghq.com))
2. **Datadog API Key** - você vai adicionar manualmente durante o deploy

## 🚀 Deploy com Datadog

### Opção 1: Script de Deploy Simplificado ⭐ (Recomendado para testes)

**Passo 1**: Configure sua API key

```bash
# Edite o script e adicione sua API key
nano deploy-with-datadog.sh

# OU crie um arquivo .env.datadog
echo "DATADOG_API_KEY=sua_chave_aqui" > .env.datadog
```

**Passo 2**: Execute o script

```bash
./deploy-with-datadog.sh
```

O script vai automaticamente:
- Fazer build do SAM
- Fazer deploy com sua API key
- Mostrar próximos passos

**Onde encontrar a API Key:**
1. Acesse: https://app.datadoghq.com/organization-settings/api-keys
2. Copie uma API key existente ou crie uma nova
3. Cole no script ou arquivo .env.datadog

### Opção 2: Deploy Interativo

```bash
sam build -t template-datadog.yaml
sam deploy --guided --template-file template-datadog.yaml
```

Durante o deploy, pressione Enter para usar o default ou cole sua API key:

```
Parameter DatadogApiKey [YOUR_DATADOG_API_KEY_HERE]: <COLE SUA API KEY OU ENTER>
```

### Opção 3: Deploy Direto (linha de comando)

```bash
sam build -t template-datadog.yaml
sam deploy \
  --template-file template-datadog.yaml \
  --parameter-overrides DatadogApiKey=<SUA_API_KEY>
```

### Opção 4: Hardcode no Template (apenas para testes locais)

⚠️ **NÃO recomendado para produção!**

Edite `template-datadog.yaml` linha 6:

```yaml
Default: "dd1234567890abcdef"  # Sua API key real
```

Depois faça deploy normal:

```bash
sam build -t template-datadog.yaml
sam deploy --template-file template-datadog.yaml
```

## 🔍 O que o Datadog vai capturar

Após o deploy, o Datadog automaticamente vai coletar:

### ✅ Traces (APM)
- Cold start duration
- Payment API latency
- DynamoDB query times
- SNS/SQS publish times
- End-to-end request traces

### ✅ Logs
- Todos os `print()` statements
- Logs estruturados com context
- Correlation entre logs e traces

### ✅ Métricas
- Lambda invocations
- Error rates
- Duration (p50, p95, p99)
- Cold starts
- Concurrent executions

### ✅ Infraestrutura
- Lambda functions
- DynamoDB tables
- SQS queues
- SNS topics

## 📊 Acessando o Datadog

Após o deploy e execução de alguns requests:

1. **APM / Traces**: https://app.datadoghq.com/apm/traces
   - Filtre por `service:ecommerce-orders`
   - Veja o breakdown de latency

2. **Serverless**: https://app.datadoghq.com/functions
   - Lista todas as Lambda functions
   - Cold starts destacados

3. **Logs**: https://app.datadoghq.com/logs
   - Pesquise por `service:ecommerce-api`
   - Veja logs correlacionados com traces

## 🐛 Debug do Problema de Timeout

Com Datadog instrumentado, você vai conseguir ver:

### No APM Trace View:
```
┌─ Lambda Invocation (9.3s) ❌ TIMEOUT
│
├─ Cold Start Init (3.0s)
│  └─ Module Loading
│
├─ DynamoDB GetItem (0.1s) ✅
│
├─ HTTP Request to Payment API (6.0s) ⚠️ BOTTLENECK
│  └─ httpbin.org/delay/6
│
└─ Lambda Timeout (5.0s) ❌
```

### No Service Map:
```
API Gateway → OrdersFunction → Payment API (slow)
            ↓
            → DynamoDB (fast)
            ↓
            → SNS/SQS (never reached)
```

### Métricas Claras:
- **Cold Start Rate**: ~15-20%
- **Error Rate**: ~15% (concentrated in cold starts)
- **P99 Latency**: 9000ms
- **Timeout Count**: High

## 🔄 Rollback para versão SEM Datadog

Se quiser voltar para a versão sem instrumentação:

```bash
sam build -t template.yaml
sam deploy
```

## 💰 Custos

**Datadog Pricing:**
- Trial gratuito: 14 dias
- Depois: ~$15/mês por host (Lambda conta como "hosts")
- Pode adicionar alertas, dashboards customizados, etc.

**AWS Lambda:**
- Datadog layers adicionam ~50MB
- Overhead de execução: +10-50ms
- Custo adicional negligível

## 📝 Configurações Importantes no Template

### Handler Redirection (Método Recomendado)

```yaml
# Lambda Function Configuration
Handler: datadog_lambda.handler.handler  # Datadog wrapper handler

Environment:
  Variables:
    DD_LAMBDA_HANDLER: handler.lambda_handler  # Seu handler original
    DD_API_KEY: !Ref DatadogApiKey
    DD_SITE: datadoghq.com
    DD_ENV: production
    DD_SERVICE: ecommerce-api
    DD_TRACE_ENABLED: true
    DD_LOGS_INJECTION: true
    DD_TRACE_SAMPLE_RATE: "1"  # 100% sampling

Layers:
  - arn:aws:lambda:us-east-1:464622532012:layer:Datadog-Extension:65
  - arn:aws:lambda:us-east-1:464622532012:layer:Datadog-Python311:115
```

**Vantagens desta abordagem:**
- ✅ Não precisa modificar código Python
- ✅ Funciona com qualquer Lambda function
- ✅ Método oficialmente recomendado pela Datadog
- ✅ Mais fácil de manter e atualizar

## 🎯 Próximos Passos

Depois do deploy com Datadog:

1. Execute o load test:
   ```bash
   python tests/test_script.py https://your-api-url 50
   ```

2. Vá para Datadog APM e veja os traces

3. Identifique os problemas:
   - Cold starts lentos
   - Payment API timeout
   - Lambda timeout muito baixo

4. Implemente as correções e compare métricas!

## 🆘 Troubleshooting

### Erro: "Layer version does not exist"
**Solução**: Atualizar versão do layer no template. Verifique a versão mais recente em:
https://docs.datadoghq.com/serverless/libraries_integrations/extension/

### Erro: "Invalid API Key"
**Solução**: Verifique se a API key está correta em:
https://app.datadoghq.com/organization-settings/api-keys

### Não vejo traces no Datadog
**Solução**:
1. Aguarde 1-2 minutos (propagação)
2. Execute alguns requests na API
3. Verifique se `DD_TRACE_ENABLED=true`
4. Verifique logs do Lambda no CloudWatch

## 📚 Recursos

- [Datadog Serverless Monitoring](https://docs.datadoghq.com/serverless/)
- [Lambda Extension](https://docs.datadoghq.com/serverless/libraries_integrations/extension/)
- [Python Tracer](https://docs.datadoghq.com/tracing/setup_overview/setup/python/)
