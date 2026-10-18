from app import app
import json

app.config['TESTING'] = True
client = app.test_client()

response = client.get('/generate?query=Norwegian+meatballs+with+seasoned+meat+cakes,+brown+gravy,+boiled+potatoes+and+lingonberry+jam&chef_id=gourmet')
print("Status Code:", response.status_code)
if response.status_code == 500:
    print(response.get_data(as_text=True))
