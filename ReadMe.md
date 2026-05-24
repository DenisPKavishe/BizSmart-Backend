curl -X POST http://127.0.0.1:8000/api/v1/financials/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MTI4MzczLCJpYXQiOjE3NzkxMjc0NzMsImp0aSI6ImNhYmFkYTc0N2QwYTRhNzBhZTM1MzQzZDc5ZDM4YmRhIiwidXNlcl9pZCI6MX0.r7hVVwBK5W_yFInXwCyR4_CfdH7b_IfFLAYqlYdV6og" \
  -d '{
    "type": "expense",
    "cost_type": "variable",
    "category": "utilities",
    "amount": 25000,
    "description": "Electricity bill",
    "transaction_date": "2026-05-18"
  }'



  # Login and get token and business ID
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@bizsmart.com","password":"123456"}')

TOKEN=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access'])")
BUSINESS_ID=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['user']['business'])")

echo "Token: $TOKEN"
echo "Business ID: $BUSINESS_ID"


curl -X POST http://127.0.0.1:8000/api/v1/financials/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"type\": \"expense\",
    \"cost_type\": \"variable\",
    \"category\": \"utilities\",
    \"amount\": 25000,
    \"description\": \"Electricity bill\",
    \"transaction_date\": \"2026-05-18\",
    \"business\": $BUSINESS_ID
  }"



  curl -X POST http://127.0.0.1:8000/api/v1/financials/invoices/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MTMwOTg0LCJpYXQiOjE3NzkxMzAwODQsImp0aSI6IjNmMTZiOWM2YzE3ZjQ4NzNhZjk0YzRiYTkwNjQ0ZDliIiwidXNlcl9pZCI6MX0.zKqGAcPcDSeHQ19LbvpUHem59dVg-LDAfML18S_yVno" \
  -d '{
    "customer": 1,
    "issue_date": "2026-05-18",
    "due_date": "2026-06-18",
    "subtotal": 100000,
    "tax_amount": 18000,
    "total_amount": 118000,
    "notes": "Test invoice",
    "items": [
      {
        "description": "Product 1",
        "quantity": 2,
        "unit_price": 50000,
        "total": 100000
      }
    ]
  }'



  curl -X POST http://127.0.0.1:8000/api/v1/financials/invoices/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MTMwOTg0LCJpYXQiOjE3NzkxMzAwODQsImp0aSI6IjNmMTZiOWM2YzE3ZjQ4NzNhZjk0YzRiYTkwNjQ0ZDliIiwidXNlcl9pZCI6MX0.zKqGAcPcDSeHQ19LbvpUHem59dVg-LDAfML18S_yVno" \
  -d '{
    "invoice_number": "INV-001",
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "0712345678",
    "issue_date": "2026-05-18",
    "due_date": "2026-06-18",
    "subtotal": 100000,
    "tax_amount": 18000,
    "total_amount": 118000,
    "business": 1,
    "notes": "Test invoice",
    "items": [
      {
        "description": "Product 1",
        "quantity": 2,
        "unit_price": 50000,
        "total": 100000
      }
    ]
  }'




  curl -X POST http://127.0.0.1:8000/api/v1/financials/loans/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MTM1MTE5LCJpYXQiOjE3NzkxMzQyMTksImp0aSI6ImZiYmZkMDI3NjkxMjQzY2JhOWYzNWNkY2Q5NjI3YTMwIiwidXNlcl9pZCI6MX0.zqqAJIF3Flhyh9Csd4OdL4Agd-szyylyFba1JLloOik" \
  -d '{
    "lender_name": "Test Bank",
    "loan_type": "bank",
    "principal_amount": 1000000,
    "interest_rate": 12,
    "term_months": 12,
    "monthly_payment": 88848,
    "start_date": "2026-05-18",
    "next_payment_date": "2026-06-18",
    "status": "active",
    "business": 1
  }'




  curl -X POST "http://localhost:8000/api/v1/hr/employees/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MjIwNTIwLCJpYXQiOjE3NzkyMTk2MjAsImp0aSI6IjQwZjI2YzBjMDdhOTQ2ZGI5Y2NmNDYxY2I1NTBhMjc1IiwidXNlcl9pZCI6MX0.GfxMoGgv10bid7U0xHTYHxaTLf2LFyqR_wpjtR_aQsg" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Updated",
    "last_name": "Name",
    "email": "updated@example.com",
    "phone": "0712345678",
    "address": "Updated Address",
    "gender": "M",
    "date_of_birth": "1990-01-01",
    "job_title": "Senior Developer",
    "employment_type": "full_time",
    "hire_date": "2024-01-01",
    "commission_rate": "10",
    "bank_name": "Updated Bank",
    "bank_account_number": "0987654321",
    "tin_number": "987654321",
    "emergency_contact_name": "Updated Contact",
    "emergency_contact_phone": "0712345679",
    "business": 1,
    "department": 1,
    "role": 1,
    "is_active": true
  }'





eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MjIzNTU5LCJpYXQiOjE3NzkyMjI2NTksImp0aSI6IjQ5MGQzYjkxNWM5MzQyMGU5NWE2MjJhMmRhYjM5NjljIiwidXNlcl9pZCI6MX0.P7GuYCCZQhS8qanUlTcsxrdndIBkdwFYs59elPaTTNY


curl -X POST "http://localhost:8000/api/v1/hr/salaries/" \
  -H "Authorization: Bearer eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MjIzNTU5LCJpYXQiOjE3NzkyMjI2NTksImp0aSI6IjQ5MGQzYjkxNWM5MzQyMGU5NWE2MjJhMmRhYjM5NjljIiwidXNlcl9pZCI6MX0.P7GuYCCZQhS8qanUlTcsxrdndIBkdwFYs59elPaTTNY" \
  -H "Content-Type: application/json" \
  -d '{
    "employee": 6,
    "effective_date": "2024-01-01",
    "base_salary": 1000000
  }'



  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MjIzOTY4LCJpYXQiOjE3NzkyMjMwNjgsImp0aSI6ImFiYzA5Y2U1YzRiNzQ0NjBhYjg1NGY1MTU4NThhNDZjIiwidXNlcl9pZCI6MX0.LIZP-42pxjlQ-7qrlAkSpe3UP8wJ_blo-8aPId_M_9o



  curl -X POST "http://localhost:8000/api/v1/hr/salaries/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5MjIzOTY4LCJpYXQiOjE3NzkyMjMwNjgsImp0aSI6ImFiYzA5Y2U1YzRiNzQ0NjBhYjg1NGY1MTU4NThhNDZjIiwidXNlcl9pZCI6MX0.LIZP-42pxjlQ-7qrlAkSpe3UP8wJ_blo-8aPId_M_9o" \
  -H "Content-Type: application/json" \
  -d '{
    "employee": 6,
    "effective_date": "2024-01-01",
    "base_salary": 1000000
  }'



  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5NjE2NzU5LCJpYXQiOjE3Nzk2MTU4NTksImp0aSI6Ijk3ZjEwN2MzZTI2ZjRhYjBiMmI0MTEwMmNkNmVjZDM4IiwidXNlcl9pZCI6MX0.3yCpFqaARH54jGQXn8x47iSZkmhdu_lxdERuPwkIyL0




  curl -X 'POST' \
  'http://localhost:8000/api/v1/hr/salaries/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc5NjE2NzU5LCJpYXQiOjE3Nzk2MTU4NTksImp0aSI6Ijk3ZjEwN2MzZTI2ZjRhYjBiMmI0MTEwMmNkNmVjZDM4IiwidXNlcl9pZCI6MX0.3yCpFqaARH54jGQXn8x47iSZkmhdu_lxdERuPwkIyL0' \
  -d '{
  "employee": 1,
  "effective_date": "2026-05-24",
  "base_salary": 1000000
}'