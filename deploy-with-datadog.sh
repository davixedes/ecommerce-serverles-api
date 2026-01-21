#!/bin/bash

# Script de deploy com Datadog
# Para fins de teste - adicione sua API key diretamente aqui

# ========================================
# CONFIGURE SUA API KEY AQUI:
# ========================================
DATADOG_API_KEY="YOUR_DATADOG_API_KEY_HERE"

# ========================================
# OU leia de um arquivo .env.datadog:
# ========================================
if [ -f ".env.datadog" ]; then
    echo "📄 Lendo API key de .env.datadog..."
    source .env.datadog
fi

# Validar se a API key foi configurada
if [ "$DATADOG_API_KEY" == "YOUR_DATADOG_API_KEY_HERE" ]; then
    echo "❌ Erro: Configure sua Datadog API key antes de fazer deploy!"
    echo ""
    echo "Opção 1: Edite este arquivo e substitua YOUR_DATADOG_API_KEY_HERE"
    echo "Opção 2: Crie um arquivo .env.datadog com DATADOG_API_KEY=sua_chave"
    echo ""
    echo "Obtenha sua API key em: https://app.datadoghq.com/organization-settings/api-keys"
    exit 1
fi

echo "🔨 Building SAM application with Datadog..."
sam build -t template-datadog.yaml

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "🚀 Deploying to AWS with Datadog instrumentation..."
echo "   API Key: ${DATADOG_API_KEY:0:8}..."
echo ""

sam deploy \
  --template-file template-datadog.yaml \
  --parameter-overrides DatadogApiKey="$DATADOG_API_KEY" \
  --no-confirm-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deploy completed successfully!"
    echo ""
    echo "🔍 Next steps:"
    echo "1. Run load test: python tests/test_script.py <API_URL> 50"
    echo "2. Check Datadog APM: https://app.datadoghq.com/apm/traces"
    echo "3. View Lambda functions: https://app.datadoghq.com/functions"
else
    echo ""
    echo "❌ Deploy failed!"
    exit 1
fi
