"""
Load Test - E-commerce Serverless
Faz múltiplas requisições para medir sucesso/falha e latência

Usage:
    python load_test.py <API_URL> [requests_per_endpoint]
    
Examples:
    python load_test.py https://abc.execute-api.us-east-1.amazonaws.com
    python load_test.py https://abc.execute-api.us-east-1.amazonaws.com 50
"""

import sys
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestResult:
    """Resultado de uma requisição"""
    def __init__(self):
        self.success = False
        self.status_code = None
        self.latency_ms = 0
        self.error = None


def test_get_products(api_url: str) -> TestResult:
    """Test GET /products"""
    result = TestResult()
    
    try:
        start = time.time()
        response = requests.get(f"{api_url}/products", timeout=10)
        result.latency_ms = (time.time() - start) * 1000
        result.status_code = response.status_code
        result.success = response.status_code == 200
        
    except requests.Timeout:
        result.latency_ms = 10000
        result.error = "timeout"
    except Exception as e:
        result.error = str(e)
    
    return result


def test_get_product_by_id(api_url: str, product_id: str) -> TestResult:
    """Test GET /products/{id}"""
    result = TestResult()
    
    try:
        start = time.time()
        response = requests.get(f"{api_url}/products/{product_id}", timeout=10)
        result.latency_ms = (time.time() - start) * 1000
        result.status_code = response.status_code
        result.success = response.status_code == 200
        
    except requests.Timeout:
        result.latency_ms = 10000
        result.error = "timeout"
    except Exception as e:
        result.error = str(e)
    
    return result


def test_create_order(api_url: str, product_id: str, customer_num: int) -> TestResult:
    """Test POST /orders"""
    result = TestResult()
    
    order_data = {
        "customer_id": f"cust-test-{customer_num:04d}",
        "items": [{"product_id": product_id, "quantity": 1}]
    }
    
    try:
        start = time.time()
        response = requests.post(
            f"{api_url}/orders",
            json=order_data,
            timeout=10
        )
        result.latency_ms = (time.time() - start) * 1000
        result.status_code = response.status_code
        
        # Sucesso é 201, mas também aceitar timeout como "esperado"
        result.success = response.status_code == 201
        
    except requests.Timeout:
        result.latency_ms = 10000
        result.status_code = 504
        result.error = "timeout"
        # Timeout é "esperado" para este endpoint
        
    except Exception as e:
        result.error = str(e)
    
    return result


def run_load_test(api_url: str, num_requests: int = 100):
    """
    Executa load test em todos os endpoints
    
    Args:
        api_url: URL da API
        num_requests: Número de requests por endpoint
    """
    
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}LOAD TEST - E-COMMERCE SERVERLESS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    print(f"API URL: {api_url}")
    print(f"Requests per endpoint: {num_requests}")
    print(f"Total requests: {num_requests * 3}\n")
    
    # Primeiro, pegar alguns product IDs
    print("🔍 Fetching product IDs...")
    try:
        response = requests.get(f"{api_url}/products", timeout=10)
        if response.status_code == 200:
            products = response.json().get('products', [])
            product_ids = [p['product_id'] for p in products[:10]]
            if not product_ids:
                print(f"{Colors.RED}❌ No products found. Run seed_products.py first!{Colors.END}")
                sys.exit(1)
            print(f"✅ Found {len(product_ids)} products\n")
        else:
            print(f"{Colors.RED}❌ Failed to fetch products{Colors.END}")
            sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        sys.exit(1)
    
    # ==========================================================================
    # TEST 1: GET /products
    # ==========================================================================
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}[1/3] Testing GET /products{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    
    results_products = []
    
    print(f"Running {num_requests} requests...", end='', flush=True)
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_get_products, api_url) for _ in range(num_requests)]
        
        for i, future in enumerate(as_completed(futures), 1):
            results_products.append(future.result())
            if i % 10 == 0:
                print(f"\rRunning {num_requests} requests... {i}/{num_requests}", end='', flush=True)
    
    total_time = time.time() - start_time
    print(f"\r✅ Completed {num_requests} requests in {total_time:.2f}s\n")
    
    # Análise
    analyze_results("GET /products", results_products)
    
    # ==========================================================================
    # TEST 2: GET /products/{id}
    # ==========================================================================
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}[2/3] Testing GET /products/{{id}}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")

    
    results_get_product = []
    
    print(f"Running {num_requests} requests...", end='', flush=True)
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(test_get_product_by_id, api_url, product_ids[i % len(product_ids)])
            for i in range(num_requests)
        ]
        
        for i, future in enumerate(as_completed(futures), 1):
            results_get_product.append(future.result())
            if i % 10 == 0:
                print(f"\rRunning {num_requests} requests... {i}/{num_requests}", end='', flush=True)
    
    total_time = time.time() - start_time
    print(f"\r✅ Completed {num_requests} requests in {total_time:.2f}s\n")
    
    # Análise
    analyze_results("GET /products/{id}", results_get_product)
    
    # ==========================================================================
    # TEST 3: POST /orders (PROBLEMÁTICO!)
    # ==========================================================================
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}[3/3] Testing POST /orders{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}")
    
    results_orders = []
    
    print(f"Running {num_requests} requests...", end='', flush=True)
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:  # Menos workers para não sobrecarregar
        futures = [
            executor.submit(test_create_order, api_url, product_ids[i % len(product_ids)], i)
            for i in range(num_requests)
        ]
        
        for i, future in enumerate(as_completed(futures), 1):
            results_orders.append(future.result())
            if i % 10 == 0:
                print(f"\rRunning {num_requests} requests... {i}/{num_requests}", end='', flush=True)
    
    total_time = time.time() - start_time
    print(f"\r✅ Completed {num_requests} requests in {total_time:.2f}s\n")
    
    # Análise
    analyze_results("POST /orders", results_orders, expect_failures=True)
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print_summary(results_products, results_get_product, results_orders)


def analyze_results(endpoint: str, results: List[TestResult], expect_failures: bool = False):
    """Analisa e mostra resultados de um endpoint"""
    
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    
    # Calcular latências apenas dos sucessos
    successful_latencies = [r.latency_ms for r in results if r.success]
    
    # Status codes
    status_codes = {}
    for r in results:
        if r.status_code:
            status_codes[r.status_code] = status_codes.get(r.status_code, 0) + 1
    
    # Timeouts
    timeouts = sum(1 for r in results if r.error == "timeout")
    
    # Print results
    print(f"{Colors.BOLD}Results:{Colors.END}")
    print(f"  Total requests:     {total}")
    
    if expect_failures:
        print(f"  {Colors.GREEN}✅ Successful:       {successful} ({successful/total*100:.1f}%){Colors.END}")
        print(f"  {Colors.YELLOW}⚠️  Failed:           {failed} ({failed/total*100:.1f}%) [EXPECTED]{Colors.END}")
        print(f"  {Colors.YELLOW}⏱️  Timeouts:         {timeouts} ({timeouts/total*100:.1f}%) [EXPECTED]{Colors.END}")
    else:
        if failed == 0:
            print(f"  {Colors.GREEN}✅ Successful:       {successful} ({successful/total*100:.1f}%){Colors.END}")
            print(f"  {Colors.GREEN}❌ Failed:           {failed} ({failed/total*100:.1f}%){Colors.END}")
        else:
            print(f"  {Colors.GREEN}✅ Successful:       {successful} ({successful/total*100:.1f}%){Colors.END}")
            print(f"  {Colors.RED}❌ Failed:           {failed} ({failed/total*100:.1f}%){Colors.END}")
    
    print(f"\n  Status Codes:")
    for code, count in sorted(status_codes.items()):
        pct = count/total*100
        if code == 200 or code == 201:
            print(f"    {Colors.GREEN}{code}: {count} ({pct:.1f}%){Colors.END}")
        elif code in [502, 504]:
            if expect_failures:
                print(f"    {Colors.YELLOW}{code}: {count} ({pct:.1f}%) [EXPECTED]{Colors.END}")
            else:
                print(f"    {Colors.RED}{code}: {count} ({pct:.1f}%){Colors.END}")
        else:
            print(f"    {code}: {count} ({pct:.1f}%)")
    
    # Latência
    if successful_latencies:
        print(f"\n  {Colors.BOLD}Latency (successful requests):{Colors.END}")
        print(f"    Min:     {min(successful_latencies):.0f}ms")
        print(f"    Max:     {max(successful_latencies):.0f}ms")
        print(f"    Average: {statistics.mean(successful_latencies):.0f}ms")
        print(f"    Median:  {statistics.median(successful_latencies):.0f}ms")
        
        if len(successful_latencies) >= 10:
            p95 = statistics.quantiles(successful_latencies, n=20)[18]
            p99 = statistics.quantiles(successful_latencies, n=100)[98]
            print(f"    P95:     {p95:.0f}ms")
            print(f"    P99:     {p99:.0f}ms")
    else:
        print(f"\n  {Colors.RED}No successful requests to calculate latency{Colors.END}")


def print_summary(results_products, results_get_product, results_orders):
    """Print resumo final"""
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")
    
    # Calcular métricas
    endpoints = [
        ("GET /products", results_products),
        ("GET /products/{id}", results_get_product),
        ("POST /orders", results_orders)
    ]
    
    print(f"{Colors.BOLD}Success Rate by Endpoint:{Colors.END}\n")
    
    for name, results in endpoints:
        total = len(results)
        successful = sum(1 for r in results if r.success)
        success_rate = successful / total * 100
        
        successful_latencies = [r.latency_ms for r in results if r.success]
        avg_latency = statistics.mean(successful_latencies) if successful_latencies else 0
        
        if success_rate >= 90:
            status = f"{Colors.GREEN}✅"
        elif success_rate >= 50:
            status = f"{Colors.YELLOW}⚠️ "
        else:
            status = f"{Colors.RED}❌"
        
        print(f"{status} {name:25} {success_rate:5.1f}% success | {avg_latency:6.0f}ms avg{Colors.END}")
    
    print(f"\n{Colors.BOLD}Analysis:{Colors.END}\n")
    
    # GET /products
    products_success = sum(1 for r in results_products if r.success) / len(results_products) * 100
    if products_success >= 95:
        print(f"{Colors.GREEN}✅ GET /products:       Working as expected{Colors.END}")
    else:
        print(f"{Colors.RED}❌ GET /products:       Unexpected failures{Colors.END}")
    
    # GET /products/{id}
    get_product_success = sum(1 for r in results_get_product if r.success) / len(results_get_product) * 100
    if get_product_success >= 95:
        print(f"{Colors.GREEN}✅ GET /products/{{id}}:   Working as expected{Colors.END}")
    else:
        print(f"{Colors.RED}❌ GET /products/{{id}}:   Unexpected failures{Colors.END}")
    
    # POST /orders
    orders_success = sum(1 for r in results_orders if r.success) / len(results_orders) * 100
    orders_timeouts = sum(1 for r in results_orders if r.error == "timeout") / len(results_orders) * 100
    
    if orders_timeouts >= 50:
        print(f"{Colors.YELLOW}⚠️  POST /orders:        High timeout rate ({orders_timeouts:.0f}%) [EXPECTED]{Colors.END}")
        print(f"    {Colors.CYAN}→ This is the PROBLEM we're demonstrating!{Colors.END}")
    elif orders_success >= 95:
        print(f"{Colors.YELLOW}⚠️  POST /orders:        Unexpectedly working (no timeouts){Colors.END}")
        print(f"    {Colors.CYAN}→ Payment API may have been fast{Colors.END}")
    else:
        print(f"{Colors.RED}❌ POST /orders:        Mixed results{Colors.END}")
    

def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Error: API URL required{Colors.END}")
        print(f"\nUsage: python {sys.argv[0]} <API_URL> [requests_per_endpoint]")
        print(f"\nExamples:")
        print(f"  python {sys.argv[0]} https://abc.execute-api.us-east-1.amazonaws.com")
        print(f"  python {sys.argv[0]} https://abc.execute-api.us-east-1.amazonaws.com 50")
        sys.exit(1)
    
    api_url = sys.argv[1].rstrip('/')
    
    # Parse número de requests
    num_requests = 100  # Default
    if len(sys.argv) > 2:
        try:
            num_requests = int(sys.argv[2])
            if num_requests <= 0:
                print(f"{Colors.RED}Error: Number of requests must be positive{Colors.END}")
                sys.exit(1)
        except ValueError:
            print(f"{Colors.RED}Error: Invalid number{Colors.END}")
            sys.exit(1)
    
    # Run load test
    run_load_test(api_url, num_requests)


if __name__ == '__main__':
    main()