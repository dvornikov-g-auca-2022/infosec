from typing import Annotated
from fastapi import FastAPI, Form

app = FastAPI()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345admin"
@app.post("/login")
def login(username: Annotated[str, Form()], password: Annotated[str, Form()]):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return "secret token"
    return "invalid credentials"