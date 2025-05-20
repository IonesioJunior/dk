from pydantic import BaseModel


class PingRequest(BaseModel):
    msg: str


# Build your DTN RPC endpoints available on syft://{datasite}/app_data/{app_name}/rpc/ping
def ping_handler(_: PingRequest) -> dict[str, str]:
    return {"message": "pong"}
