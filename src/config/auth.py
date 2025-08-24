from fastapi import HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode
from typing import Optional, Dict, Any
import httpx
from .settings import settings
import logging
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure DEBUG logs are emitted even if root/uvicorn handlers filter them.
# Avoid duplicate handlers on reload and stop propagation to root.
# Force any pre-attached handlers (e.g., from Uvicorn) to DEBUG
for _h in logger.handlers:
    _h.setLevel(logging.DEBUG)

# Add our own handler once
if not any(getattr(h, "_auth_debug", False) for h in logger.handlers):
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s - %(message)s"))
    setattr(_handler, "_auth_debug", True)
    logger.addHandler(_handler)
logger.propagate = False

# Use auto_error=False so we can intercept missing headers and log them before FastAPI raises
security = HTTPBearer(auto_error=False)


class ClerkAuth:
    def __init__(self):
        self.clerk_secret_key = settings.clerk_secret_key
        # Optional overrides from settings; if unset, derive from token claims
        self.expected_issuer: Optional[str] = getattr(settings, "clerk_issuer", None)
        self.expected_audience: Optional[str] = getattr(settings, "clerk_audience", None)
        # Simple in-memory JWKS cache: { issuer: {"keys": [...], "ts": epoch_seconds} }
        self._jwks_cache: Dict[str, Dict[str, Any]] = {}
        self._jwks_ttl_seconds: int = 600

    async def _fetch_jwks(self, issuer: str) -> Dict[str, Any]:
        """Fetch JWKS from issuer's well-known endpoint."""
        jwks_url = issuer.rstrip("/") + "/.well-known/jwks.json"
        logger.debug("[ClerkAuth._fetch_jwks] Fetching JWKS | url=%s", jwks_url)
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_url, timeout=5.0)
            if resp.status_code != 200:
                logger.warning(
                    "[ClerkAuth._fetch_jwks] Failed to fetch JWKS | status=%s body=%s",
                    resp.status_code,
                    resp.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to fetch JWKS for issuer",
                )
            return resp.json()

    async def _get_jwks(self, issuer: str) -> Dict[str, Any]:
        now = int(time.time())
        cached = self._jwks_cache.get(issuer)
        if cached and (now - cached.get("ts", 0) < self._jwks_ttl_seconds):
            return cached["jwks"]
        jwks = await self._fetch_jwks(issuer)
        self._jwks_cache[issuer] = {"jwks": jwks, "ts": now}
        return jwks

    async def verify_clerk_token(self, token: str) -> dict:
        """Verify Clerk JWT token locally using JWKS (no network call to Clerk per request).

        - Extract unverified header/claims to determine issuer and key id (kid)
        - Fetch and cache JWKS from issuer
        - Verify signature with matching JWK
        - Validate exp/nbf and issuer; optionally validate audience if configured
        - Return a user dict with at least 'user_id' (mapped from 'sub')
        """
        try:
            logger.debug(
                "[ClerkAuth.verify_clerk_token] Start | token_present=%s token_prefix=%s",
                bool(token),
                (token[:12] + "...") if token else None,
            )
            if not token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

            # Extract unverified header and claims
            try:
                header = jwt.get_unverified_header(token)
                claims = jwt.get_unverified_claims(token)
            except Exception as e:
                logger.warning("[ClerkAuth.verify_clerk_token] Unable to parse token: %s", e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

            alg = header.get("alg")
            kid = header.get("kid")
            if alg not in ("RS256", "RS512"):
                logger.warning("[ClerkAuth.verify_clerk_token] Unsupported alg: %s", alg)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported token algorithm")
            if not kid:
                logger.warning("[ClerkAuth.verify_clerk_token] Missing kid in header")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

            issuer = self.expected_issuer or claims.get("iss")
            if not issuer or not isinstance(issuer, str) or not issuer.startswith("http"):
                logger.warning("[ClerkAuth.verify_clerk_token] Missing/invalid issuer: %s", issuer)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")

            # Get JWKS and find the matching key
            jwks = await self._get_jwks(issuer)
            keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
            rsa_key = next((k for k in keys if k.get("kid") == kid), None)
            if not rsa_key:
                # Refresh once in case of rotation
                logger.info("[ClerkAuth.verify_clerk_token] kid not found; refreshing JWKS")
                jwks = await self._fetch_jwks(issuer)
                self._jwks_cache[issuer] = {"jwks": jwks, "ts": int(time.time())}
                keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
                rsa_key = next((k for k in keys if k.get("kid") == kid), None)
            if not rsa_key:
                logger.warning("[ClerkAuth.verify_clerk_token] kid %s not present in JWKS", kid)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token key")

            # Verify signature
            try:
                public_key = jwk.construct(rsa_key, algorithm=alg)
                signing_input, encoded_sig = str(token).rsplit(".", 1)
                decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))
                if not public_key.verify(signing_input.encode("utf-8"), decoded_sig):
                    logger.warning("[ClerkAuth.verify_clerk_token] Signature verification failed")
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("[ClerkAuth.verify_clerk_token] Error verifying signature: %s", e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

            # Validate standard claims
            now = int(time.time())
            exp = claims.get("exp")
            nbf = claims.get("nbf")
            if exp is not None and now >= int(exp):
                logger.info("[ClerkAuth.verify_clerk_token] Token expired | exp=%s now=%s", exp, now)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
            if nbf is not None and now < int(nbf):
                logger.info("[ClerkAuth.verify_clerk_token] Token not yet valid | nbf=%s now=%s", nbf, now)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not yet valid")

            token_iss = claims.get("iss")
            if self.expected_issuer and token_iss != self.expected_issuer:
                logger.warning("[ClerkAuth.verify_clerk_token] Issuer mismatch | token_iss=%s expected=%s", token_iss, self.expected_issuer)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")

            if self.expected_audience is not None:
                aud = claims.get("aud")
                if isinstance(aud, str):
                    valid_aud = aud == self.expected_audience
                elif isinstance(aud, (list, tuple)):
                    valid_aud = self.expected_audience in aud
                else:
                    valid_aud = False
                if not valid_aud:
                    logger.warning("[ClerkAuth.verify_clerk_token] Audience mismatch | aud=%s expected=%s", aud, self.expected_audience)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token audience")

            user_id = claims.get("sub") or claims.get("user_id")
            if not user_id:
                logger.warning("[ClerkAuth.verify_clerk_token] Missing subject/user_id in claims")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

            user_data = {**claims, "user_id": user_id}
            logger.debug(
                "[ClerkAuth.verify_clerk_token] Verification OK | user_id=%s keys=%s",
                user_id,
                list(user_data.keys()) if isinstance(user_data, dict) else type(user_data).__name__,
            )
            return user_data
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("[ClerkAuth.verify_clerk_token] Unexpected error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )


clerk_auth = ClerkAuth()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Get current user from Clerk token"""
    try:
        if not credentials or not credentials.credentials:
            logger.warning("[get_current_user] Missing Authorization Bearer token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        logger.debug(
            "[get_current_user] Received token | prefix=%s length=%s",
            (token[:12] + "...") if token else None,
            len(token) if token else 0,
        )
        # Dev auth bypass: only when DEBUG and explicitly enabled via env
        try:
            if settings.debug and getattr(settings, "dev_auth_bypass", False) and getattr(settings, "dev_bearer_token", None):
                if token == settings.dev_bearer_token:
                    fake_user_id = getattr(settings, "dev_fake_user_id", None) or "dev-user"
                    logger.debug("[get_current_user] DEV AUTH BYPASS active | user_id=%s", fake_user_id)
                    return {"user_id": fake_user_id, "provider": "dev_bypass"}
                else:
                    logger.debug("[get_current_user] Dev bypass enabled but token mismatch")
        except Exception as e:
            # Never fail auth due to bypass branch errors; proceed to normal verification
            logger.debug("[get_current_user] Dev bypass check error: %s", e)

        user_data = await clerk_auth.verify_clerk_token(token)
        logger.debug(
            "[get_current_user] Verified user | keys=%s",
            list(user_data.keys()) if isinstance(user_data, dict) else type(user_data).__name__,
        )
        return user_data
    except HTTPException as he:
        logger.warning("[get_current_user] Auth failed | status=%s detail=%s", he.status_code, he.detail)
        raise
    except Exception as e:
        logger.exception("[get_current_user] Unexpected error during auth: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Get current user from Clerk token (optional)"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except:
        return None
