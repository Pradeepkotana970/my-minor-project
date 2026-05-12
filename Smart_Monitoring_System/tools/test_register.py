import requests
url = 'http://localhost:5000/api/register'
files = {'image_0': open('../dataset/a_2_0.jpg','rb')}
data = {'name':'unittest_user','email':'test@example.com','phone':'1234567890','method':'api'}
print('Posting to', url)
r = requests.post(url, data=data, files=files)
print('Status:', r.status_code)
try:
    print(r.json())
except Exception as e:
    print('Response text:', r.text)
