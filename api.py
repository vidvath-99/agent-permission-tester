import os
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from gateway import Gateway


def create_app():
    token_a = os.environ.get("DEMO_TOKEN_A", "")
    token_b = os.environ.get("DEMO_TOKEN_B", "")

    if (
        len(token_a) < 32
        or len(token_b) < 32
        or token_a == token_b
    ):
        raise RuntimeError(
            "Set distinct DEMO_TOKEN_A and DEMO_TOKEN_B values "
            "of at least 32 characters before starting the API."
        )

    gateway = Gateway(broken=False)
    gateway.identities["company-b-agent"] = {
        "tenant": "company-b",
        "scopes": {"tickets:read"},
        "active": True,
    }

    app = FastAPI(title="Local Permission Testing Demo")
    app.state.gateway = gateway
    security = HTTPBearer(auto_error=False)

    def authenticate(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(security),
        ],
    ):
        if credentials is not None:
            supplied = credentials.credentials.encode("utf-8")

            for token, agent_id in (
                (token_a, "soc-agent"),
                (token_b, "company-b-agent"),
            ):
                if secrets.compare_digest(
                    supplied, token.encode("utf-8")
                ):
                    return agent_id

        raise HTTPException(
            status_code=401,
            detail="Invalid or missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def execute(agent_id, tool, ticket_id):
        try:
            return gateway.call(agent_id, tool, ticket_id)
        except PermissionError as error:
            reason = str(error)

            if reason in {"tenant_mismatch", "resource_unavailable"}:
                raise HTTPException(
                    status_code=404,
                    detail="Ticket unavailable",
                ) from error

            raise HTTPException(
                status_code=403,
                detail="Action not permitted",
            ) from error

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/tickets/{ticket_id}")
    def read_ticket(
        ticket_id: str,
        agent_id: Annotated[str, Depends(authenticate)],
    ):
        return execute(agent_id, "tickets:read", ticket_id)

    @app.delete("/tickets/{ticket_id}")
    def delete_ticket(
        ticket_id: str,
        agent_id: Annotated[str, Depends(authenticate)],
    ):
        return execute(agent_id, "tickets:delete", ticket_id)

    return app
