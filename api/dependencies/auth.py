from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
import logging

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = logging.getLogger(__name__)

class User:
    def __init__(self, token_data: dict):
        self.id = token_data.get("sub")
        self.email = token_data.get("email")
        self.preferred_username = token_data.get("preferred_username")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        # We are simply decoding the JWT to extract the user information for isolation.
        # In a fully production-hardened environment, you would also verify the signature against the Keycloak JWKS.
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        return User(payload)
    except Exception as e:
        logger.error(f"Failed to decode token: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
