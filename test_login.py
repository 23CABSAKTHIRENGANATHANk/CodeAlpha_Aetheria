import requests
import uuid

session = requests.Session()
url = "https://code-alpha-aetheria-nu2beziwb-23cabsakthirenganathanks-projects.vercel.app"

username = f"user_{uuid.uuid4().hex[:8]}"
password = "TestPassword123!"

# Register
res = session.get(f"{url}/register/")
csrf_token = session.cookies.get('csrftoken')

reg_data = {
    'username': username,
    'password': password,
    'csrfmiddlewaretoken': csrf_token
}
reg_res = session.post(f"{url}/register/", data=reg_data, headers={'Referer': f"{url}/register/"}, allow_redirects=False)
print(f"Register status: {reg_res.status_code}")

if reg_res.status_code == 302:
    print(f"Registered successfully! Location: {reg_res.headers.get('Location')}")
else:
    print("Registration failed.")
    print(reg_res.text[:500])

# Now Login
res = session.get(f"{url}/login/")
csrf_token = session.cookies.get('csrftoken')
login_data = {
    'username': username,
    'password': password,
    'csrfmiddlewaretoken': csrf_token
}
login_res = session.post(f"{url}/login/", data=login_data, headers={'Referer': f"{url}/login/"}, allow_redirects=False)
print(f"Login status: {login_res.status_code}")

if login_res.status_code == 302:
    print(f"Login success! Location: {login_res.headers.get('Location')}")
    # Fetch Feed
    feed_res = session.get(f"{url}/feed/", allow_redirects=False)
    print(f"Feed status: {feed_res.status_code}")
else:
    print("Login failed.")

