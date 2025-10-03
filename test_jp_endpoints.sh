#!/bin/bash
# Test Japanese stock endpoint with authentication

# First, login to get a token (replace with your actual credentials)
echo "Testing Japanese stock endpoints..."
echo "=================================="

# Test without auth (should get 401)
echo -e "\n1. Testing without authentication:"
curl -s http://127.0.0.1:8000/dashboard/jp/quote/7203.T | jq -r '.detail' 2>/dev/null || echo "Needs authentication ✓"

# Test OPTIONS request for CORS
echo -e "\n2. Testing CORS preflight (OPTIONS):"
curl -s -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" \
  http://127.0.0.1:8000/dashboard/jp/quote/7203.T \
  -v 2>&1 | grep -i "access-control"

echo -e "\n3. Available dashboard routes:"
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
paths = data.get('paths', {})
dashboard_paths = {k: v for k, v in paths.items() if k.startswith('/dashboard')}
for path in sorted(dashboard_paths.keys()):
    methods = list(dashboard_paths[path].keys())
    print(f'  {path:50s} {methods}')
" 2>/dev/null || echo "Could not parse OpenAPI spec"

echo -e "\nDone!"
