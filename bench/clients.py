"""Client definitions and Docker image management."""

from dataclasses import dataclass


@dataclass
class Client:
    """Execution client definition."""

    name: str
    networks: list[str]
    image: str
    chain_flag: dict[str, str]  # network -> chain flag


# All supported clients
CLIENTS: dict[str, Client] = {
    "reth": Client(
        name="reth",
        networks=["ethereum-mainnet"],
        image="ghcr.io/paradigmxyz/reth",
        chain_flag={"ethereum-mainnet": "--chain mainnet"},
    ),
    "op-reth": Client(
        name="op-reth",
        networks=["worldchain-mainnet"],
        image="ghcr.io/paradigmxyz/op-reth",
        chain_flag={"worldchain-mainnet": "--chain worldchain"},
    ),
    "nethermind": Client(
        name="nethermind",
        networks=["ethereum-mainnet", "worldchain-mainnet"],
        image="nethermind/nethermind",
        chain_flag={
            "ethereum-mainnet": "--config mainnet",
            "worldchain-mainnet": "--config worldchain",
        },
    ),
    "geth": Client(
        name="geth",
        networks=["ethereum-mainnet"],
        image="ethereum/client-go",
        chain_flag={"ethereum-mainnet": ""},
    ),
    "op-geth": Client(
        name="op-geth",
        networks=["worldchain-mainnet"],
        image="us-docker.pkg.dev/oplabs-tools-artifacts/images/op-geth",
        chain_flag={"worldchain-mainnet": ""},
    ),
}


def get_client(name: str) -> Client:
    """Get client by name."""
    if name not in CLIENTS:
        valid = ", ".join(CLIENTS.keys())
        raise ValueError(f"Unknown client: {name}. Valid clients: {valid}")
    return CLIENTS[name]


def validate_client_network(client_name: str, network: str) -> None:
    """Validate that a client supports a network."""
    client = get_client(client_name)
    if network not in client.networks:
        valid = ", ".join(client.networks)
        raise ValueError(f"Client {client_name} does not support {network}. Valid networks: {valid}")


def get_docker_image(client_name: str, version: str = "latest") -> str:
    """Get Docker image tag for a client version."""
    client = get_client(client_name)

    # Handle special version names
    if version in ("latest", "nightly"):
        return f"{client.image}:{version}"

    # Assume version is a tag (e.g., v1.0.0)
    return f"{client.image}:{version}"


def get_node_cmd(client_name: str, network: str, datadir: str = "/data") -> list[str]:
    """Get the command to start a node for benchmarking."""
    client = get_client(client_name)
    chain_flag = client.chain_flag.get(network, "")

    jwt_path = f"{datadir}/jwt.hex"

    if client_name in ("reth", "op-reth"):
        cmd = [
            "node",
            "--datadir", datadir,
            "--http",
            "--http.addr", "0.0.0.0",
            "--http.api", "admin,net,eth,web3,debug,trace",
            "--authrpc.addr", "0.0.0.0",
            "--authrpc.port", "8551",
            "--authrpc.jwtsecret", jwt_path,
            "--engine.accept-execution-requests-hash",
        ]
        if chain_flag:
            cmd.extend(chain_flag.split())
        return cmd

    elif client_name == "nethermind":
        db_subdir = "worldchain" if "worldchain" in network else "mainnet"
        cmd = [
            "--datadir", datadir,
            "--Init.BaseDbPath", f"{datadir}/{db_subdir}",
            "--JsonRpc.Enabled", "true",
            "--JsonRpc.Host", "0.0.0.0",
            "--JsonRpc.EngineHost", "0.0.0.0",
            "--JsonRpc.EnginePort", "8551",
            "--JsonRpc.JwtSecretFile", jwt_path,
        ]
        if chain_flag:
            cmd.extend(chain_flag.split())
        return cmd

    elif client_name in ("geth", "op-geth"):
        cmd = [
            "--datadir", datadir,
            "--http",
            "--http.addr", "0.0.0.0",
            "--http.api", "admin,net,eth,web3,debug",
            "--authrpc.addr", "0.0.0.0",
            "--authrpc.port", "8551",
            "--authrpc.jwtsecret", jwt_path,
        ]
        return cmd

    raise ValueError(f"No node command defined for {client_name}")


