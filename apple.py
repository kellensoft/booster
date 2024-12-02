import os
import random
import time
import datetime
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
QUERY = """
query($cursor: String) {
  users: search(query: "type:user", type: USER, first: 100, after: $cursor) {
    edges { node { ... on User { login } } }
    pageInfo { endCursor hasNextPage }
  }
}
"""

API_ENDPOINT = os.getenv("TARGET_API_URL")

def fetch_users(cursor=None):
    response = requests.post(
        "https://api.github.com/graphql",
        headers=HEADERS,
        json={"query": QUERY, "variables": {"cursor": cursor}},
    )
    data = response.json()["data"]["users"]
    return [user["node"]["login"] for user in data["edges"]], data["pageInfo"]

def get_jwt_token():
    alg = os.getenv("TARGET_API_JWT_ALG")
    issuer = os.getenv("TARGET_API_JWT_ISSUER")
    secret = os.getenv("TARGET_API_JWT_SECRET")
    if not secret:
        raise ValueError("API_SECRET environment variable is not set")
    payload = {
        "iss": issuer,
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm=alg).decode('utf-8')

def generate_png(username, number, count):
    jwt_token = get_jwt_token()
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(
        f"{API_ENDPOINT}/user/{username}?number={number}",
        headers=headers,
    )
    if response.status_code == 200:
        file_path = f"Card_{count}.png"
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Saved {file_path}")
        return True
    return False

def try_generate_png(username, number, count, retries=1, wait_time=60):
    for _ in range(retries):
        if generate_png(username, number, count):
            return True
        print(f"Failed to generate image for {username}, retrying in {wait_time} seconds...")
        time.sleep(wait_time)
    return False

def get_last_number():
    if not os.path.exists("README.md"):
        return 1
    with open("README.md", "r") as f:
        lines = f.readlines()
    numbers = [
        int(line.split(".")[0]) for line in lines if line.strip() and line[0].isdigit()
    ]
    return max(numbers, default=0)

if os.path.exists("README.md"):
    with open("README.md", "r") as f:
        readme_lines = f.readlines()
    existing_names = {line.split(". ")[-1].strip() for line in readme_lines if line.strip() and line[0].isdigit()}
else:
    existing_names = set()
    readme_lines = ["# booster\n"]

random_users, cursor = [], None

count = 1

while len(random_users) < 10:
    users, page_info = fetch_users(cursor)
    available = set(users) - existing_names
    for username in list(available):
        if len(random_users) >= 10:
            break
        number = len(random_users) + 1
        if try_generate_png(username, number, count, retries=2):
            count+=1
            random_users.append(username)
            existing_names.add(username)
        else:
            print(f"Skipping {username} due to repeated failures.")
    cursor = page_info["endCursor"]
    if not page_info["hasNextPage"] and len(random_users) < 10:
        break

updated_lines = readme_lines[:1] + [f"{i+1}. {name}\n" for i, name in enumerate(existing_names)]

with open("README.md", "w") as f:
    f.writelines(updated_lines)