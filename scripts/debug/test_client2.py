from app import app
app.config['TESTING'] = True
client = app.test_client()

response = client.get('/generate?query=Norwegian+meatballs+with+seasoned+meat+cakes,+brown+gravy,+boiled+potatoes+and+lingonberry+jam&chef_id=gourmet', follow_redirects=True)
print("Status Code:", response.status_code)
if response.status_code >= 400:
    print(response.get_data(as_text=True))
