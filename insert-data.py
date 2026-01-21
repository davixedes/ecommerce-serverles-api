# seed_data.py
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
products_table = dynamodb.Table('ecommerce-products')

products = [
    {
        'product_id': 'prod-001',
        'name': 'Wireless Headphones',
        'price': Decimal('79.99'),
        'stock_quantity': 50,
        'category': 'Electronics',
        'description': 'Premium wireless headphones with noise cancellation',
        'image_url': 'https://example.com/headphones.jpg'
    },
    {
        'product_id': 'prod-002',
        'name': 'Running Shoes',
        'price': Decimal('129.99'),
        'stock_quantity': 30,
        'category': 'Sports',
        'description': 'Professional running shoes for athletes',
        'image_url': 'https://example.com/shoes.jpg'
    },
    {
        'product_id': 'prod-003',
        'name': 'Coffee Maker',
        'price': Decimal('49.99'),
        'stock_quantity': 20,
        'category': 'Home',
        'description': 'Automatic coffee maker with timer',
        'image_url': 'https://example.com/coffee.jpg'
    },
    {
        'product_id': 'prod-004',
        'name': 'Yoga Mat',
        'price': Decimal('29.99'),
        'stock_quantity': 100,
        'category': 'Sports',
        'description': 'Non-slip yoga mat with carrying strap',
        'image_url': 'https://example.com/yoga.jpg'
    },
    {
        'product_id': 'prod-005',
        'name': 'Laptop Stand',
        'price': Decimal('39.99'),
        'stock_quantity': 45,
        'category': 'Electronics',
        'description': 'Ergonomic laptop stand with adjustable height',
        'image_url': 'https://example.com/stand.jpg'
    },
    {
        'product_id': 'prod-006',
        'name': 'Water Bottle',
        'price': Decimal('19.99'),
        'stock_quantity': 200,
        'category': 'Sports',
        'description': 'Insulated stainless steel water bottle',
        'image_url': 'https://example.com/bottle.jpg'
    },
    {
        'product_id': 'prod-007',
        'name': 'Bluetooth Speaker',
        'price': Decimal('59.99'),
        'stock_quantity': 60,
        'category': 'Electronics',
        'description': 'Portable waterproof bluetooth speaker',
        'image_url': 'https://example.com/speaker.jpg'
    },
    {
        'product_id': 'prod-008',
        'name': 'Desk Lamp',
        'price': Decimal('34.99'),
        'stock_quantity': 75,
        'category': 'Home',
        'description': 'LED desk lamp with touch controls',
        'image_url': 'https://example.com/lamp.jpg'
    }
]

print("🌱 Seeding products database...")
print(f"   Inserting {len(products)} products...\n")

for product in products:
    try:
        products_table.put_item(Item=product)
        print(f"✅ Added: {product['name']} (${product['price']}) - Stock: {product['stock_quantity']}")
    except Exception as e:
        print(f"❌ Failed to add {product['name']}: {str(e)}")

print(f"\n✅ Seed data inserted successfully!")
print(f"   Total products: {len(products)}")