import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException

class JWTHandler:
    def __init__(self, secret_key: str, algorithm: str = "HS256", expire_minutes: int = 60):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_token(self, payload: dict) -> str:
        to_encode = payload.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def decode_without_verify(self, token: str) -> dict:
        return jwt.decode(token, options={"verify_signature": False})
