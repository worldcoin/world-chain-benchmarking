"""Client definitions and Docker image management."""

from abc import ABC, abstractmethod


class Client(ABC):
    """Base class for execution clients."""

    name: str
    networks: list[str]
    image: str

    @abstractmethod
    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]: ...

    def validate_network(self, network: str) -> None:
        """Validate that this client supports the given network."""
        if network not in self.networks:
            valid = ", ".join(self.networks)
            raise ValueError(
                f"Client {self.name} does not support {network}. Valid networks: {valid}"
            )


class Reth(Client):
    name = "reth"
    networks = ["ethereum-mainnet"]
    image = "ghcr.io/paradigmxyz/reth:latest"
    chain_flag = "--chain mainnet"

    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]:
        jwt_path = f"{datadir}/jwt.hex"
        cmd = [
            "node",
            "--datadir",
            datadir,
            "--http",
            "--http.addr",
            "0.0.0.0",
            "--http.api",
            "admin,net,eth,web3,debug,trace",
            "--authrpc.addr",
            "0.0.0.0",
            "--authrpc.port",
            "8551",
            "--authrpc.jwtsecret",
            jwt_path,
            "--engine.accept-execution-requests-hash",
        ]
        if self.chain_flag:
            cmd.extend(self.chain_flag.split())
        return cmd


class OpReth(Client):
    name = "op-reth"
    networks = ["worldchain-mainnet"]
    image = "ghcr.io/paradigmxyz/op-reth:latest"
    chain_flag = "--chain worldchain"

    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]:
        jwt_path = f"{datadir}/jwt.hex"
        cmd = [
            "node",
            "--datadir",
            datadir,
            "--http",
            "--http.addr",
            "0.0.0.0",
            "--http.api",
            "admin,net,eth,web3,debug,trace",
            "--authrpc.addr",
            "0.0.0.0",
            "--authrpc.port",
            "8551",
            "--authrpc.jwtsecret",
            jwt_path,
            "--engine.accept-execution-requests-hash",
        ]
        if self.chain_flag:
            cmd.extend(self.chain_flag.split())
        return cmd


class Nethermind(Client):
    name = "nethermind"
    networks = ["ethereum-mainnet", "worldchain-mainnet"]
    image = "nethermind/nethermind:latest"
    chain_flags = {
        "ethereum-mainnet": "--config mainnet",
        "worldchain-mainnet": "--config worldchain",
    }

    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]:
        jwt_path = f"{datadir}/jwt.hex"
        db_subdir = "worldchain" if "worldchain" in network else "mainnet"
        cmd = [
            "--datadir",
            datadir,
            "--Init.BaseDbPath",
            f"{datadir}/{db_subdir}",
            "--JsonRpc.Enabled",
            "true",
            "--JsonRpc.Host",
            "0.0.0.0",
            "--JsonRpc.EngineHost",
            "0.0.0.0",
            "--JsonRpc.EnginePort",
            "8551",
            "--JsonRpc.JwtSecretFile",
            jwt_path,
        ]
        chain_flag = self.chain_flags.get(network, "")
        if chain_flag:
            cmd.extend(chain_flag.split())
        return cmd


class Geth(Client):
    name = "geth"
    networks = ["ethereum-mainnet"]
    image = "ethpandaops/geth:performance"

    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]:
        jwt_path = f"{datadir}/jwt.hex"
        return [
            "--datadir",
            datadir,
            "--http",
            "--http.addr",
            "0.0.0.0",
            "--http.api",
            "admin,net,eth,web3,debug",
            "--authrpc.addr",
            "0.0.0.0",
            "--authrpc.port",
            "8551",
            "--authrpc.jwtsecret",
            jwt_path,
            "--state.scheme=path",
            "--cache.preimages",
            "--nodiscover",
            "--maxpeers=0",
            "--mainnet",
            "--syncmode=full",
        ]


class OpGeth(Client):
    name = "op-geth"
    networks = ["worldchain-mainnet"]
    image = "us-docker.pkg.dev/oplabs-tools-artifacts/images/op-geth:latest"

    def get_node_cmd(self, network: str, datadir: str = "/data") -> list[str]:
        jwt_path = f"{datadir}/jwt.hex"
        return [
            "--datadir",
            datadir,
            "--http",
            "--http.addr",
            "0.0.0.0",
            "--http.api",
            "admin,net,eth,web3,debug",
            "--authrpc.addr",
            "0.0.0.0",
            "--authrpc.port",
            "8551",
            "--authrpc.jwtsecret",
            jwt_path,
        ]


# Client registry
CLIENTS: dict[str, Client] = {
    "reth": Reth(),
    "op-reth": OpReth(),
    "nethermind": Nethermind(),
    "geth": Geth(),
    "op-geth": OpGeth(),
}


def get_client(name: str) -> Client:
    """Get client by name."""
    if name not in CLIENTS:
        valid = ", ".join(CLIENTS.keys())
        raise ValueError(f"Unknown client: {name}. Valid clients: {valid}")
    return CLIENTS[name]
