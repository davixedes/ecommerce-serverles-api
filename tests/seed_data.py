"""
Seed Products Script
Popula a tabela DynamoDB com produtos de teste

Usage:
    python seed_products.py [num_products]
    
Examples:
    python seed_products.py           # 50 produtos (default)
    python seed_products.py 100       # 100 produtos
    python seed_products.py 1000      # 1000 produtos
"""

import sys
import boto3
import random
from decimal import Decimal
from faker import Faker

# Configuração
dynamodb = boto3.resource('dynamodb')
fake = Faker()

TABLE_NAME = 'ecommerce-products'

CATEGORIES = [
    'electronics',
    'clothing', 
    'home',
    'sports',
    'toys',
    'books',
    'automotive',
    'beauty',
    'health',
    'garden'
]

BRANDS = [
    'TechPro', 'StyleCo', 'HomeMax', 'SportFit', 'PlayTime',
    'ReadWell', 'AutoParts', 'GlowBeauty', 'HealthPlus', 'GreenThumb'
]


def generate_product(product_num: int) -> dict:
    """Gera um produto fake realista"""
    
    category = random.choice(CATEGORIES)
    brand = random.choice(BRANDS)
    
    return {
        'product_id': f'prod-{product_num:04d}',
        'name': f'{brand} {fake.catch_phrase()}',
        'category': category,
        'price': Decimal(str(round(random.uniform(9.99, 999.99), 2))),
        'stock': random.randint(0, 200),
        'description': fake.text(max_nb_chars=200),
        'brand': brand,
        'rating': Decimal(str(round(random.uniform(1.0, 5.0), 1))),
        'reviews_count': random.randint(0, 500),
        'weight_kg': Decimal(str(round(random.uniform(0.1, 50.0), 2))),
        'dimensions': f"{random.randint(10,100)}x{random.randint(10,100)}x{random.randint(5,50)}cm",
        'in_stock': random.choice([True, False]),
        'featured': random.choice([True, False]),
        'discount_percent': Decimal(str(random.choice([0, 5, 10, 15, 20, 25])))
    }


def seed_products(num_products: int = 50):
    """
    Popula a tabela Products com dados fake
    
    Args:
        num_products: Número de produtos a criar (default: 50)
    """
    
    print(f"🚀 Starting seed process...")
    print(f"📦 Table: {TABLE_NAME}")
    print(f"🔢 Products to create: {num_products}")
    print()
    
    try:
        products_table = dynamodb.Table(TABLE_NAME)
        
        # Verificar se tabela existe
        products_table.load()
        print(f"✅ Table '{TABLE_NAME}' found")
        
    except Exception as e:
        print(f"❌ Error: Table '{TABLE_NAME}' not found!")
        print(f"   Make sure the stack is deployed.")
        print(f"   Error: {str(e)}")
        sys.exit(1)
    
    print()
    print(f"📝 Generating {num_products} products...")
    
    # Usar batch_writer para eficiência
    successful = 0
    failed = 0
    
    with products_table.batch_writer() as batch:
        for i in range(1, num_products + 1):
            try:
                product = generate_product(i)
                batch.put_item(Item=product)
                successful += 1
                
                # Progress indicator
                if i % 10 == 0:
                    print(f"   Inserted {i}/{num_products} products...", end='\r')
                
            except Exception as e:
                failed += 1
                print(f"\n   ⚠️  Failed to insert product {i}: {str(e)}")
    
    print(f"\n\n{'='*60}")
    print(f"✅ SEED COMPLETED!")
    print(f"{'='*60}")
    print(f"✅ Successfully inserted: {successful} products")
    if failed > 0:
        print(f"❌ Failed: {failed} products")
    print(f"📊 Total in table: {successful} products")
    print()
    
    # Mostrar alguns produtos de exemplo
    print("📦 Sample Products:")
    print("-" * 60)
    
    try:
        response = products_table.scan(Limit=5)
        for product in response.get('Items', []):
            print(f"  • {product['product_id']}: {product['name']}")
            print(f"    Category: {product['category']} | Price: ${product['price']} | Stock: {product['stock']}")
    except Exception as e:
        print(f"  Could not fetch sample products: {str(e)}")
    
    print()


def main():
    """Main function"""
    
    # Parse argumentos
    num_products = 50  # Default
    
    if len(sys.argv) > 1:
        try:
            num_products = int(sys.argv[1])
            if num_products <= 0:
                print("❌ Error: Number of products must be positive")
                sys.exit(1)
        except ValueError:
            print("❌ Error: Invalid number")
            print(f"Usage: python {sys.argv[0]} [num_products]")
            sys.exit(1)
    
    # Executar seed
    seed_products(num_products)


if __name__ == '__main__':
    main()