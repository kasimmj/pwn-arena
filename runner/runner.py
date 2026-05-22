"""pwn-arena container runner — spawns isolated challenge containers per user."""

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Optional

import docker
from docker.errors import APIError, ImageNotFound


@dataclass
class Instance:
    user_id: str
    challenge_id: str
    container_id: str
    flag: str
    network_id: str
    port_map: dict[str, int]
    expires_at: float


class Runner:
    """Manages per-user-per-challenge container lifecycles."""

    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self.client = docker_client or docker.from_env()
        self.instances: dict[str, Instance] = {}
        self.lock = threading.Lock()

    def _user_network(self, user_id: str):
        name = f"arena-user-{user_id}"
        try:
            return self.client.networks.get(name)
        except docker.errors.NotFound:
            return self.client.networks.create(
                name,
                driver="bridge",
                internal=True,
                labels={"arena.user": user_id},
            )

    def spawn(
        self,
        user_id: str,
        challenge_id: str,
        image: str,
        ports: list[int],
        flag_env: str = "FLAG",
        timeout_seconds: int = 1800,
        privileged: bool = False,
    ) -> Instance:
        """Spawn an isolated challenge container for this user."""

        key = f"{user_id}:{challenge_id}"
        with self.lock:
            if key in self.instances:
                self._kill_unsafe(key)

            flag = self._generate_flag(challenge_id, user_id)
            network = self._user_network(user_id)

            try:
                container = self.client.containers.run(
                    image,
                    detach=True,
                    auto_remove=True,
                    network=network.name,
                    privileged=privileged,
                    environment={flag_env: flag},
                    ports={f"{p}/tcp": None for p in ports},
                    mem_limit="512m",
                    cpu_period=100_000,
                    cpu_quota=50_000,  # 0.5 CPU
                    pids_limit=128,
                    read_only=False,
                    labels={
                        "arena.user": user_id,
                        "arena.challenge": challenge_id,
                    },
                )
            except ImageNotFound:
                raise RuntimeError(f"Challenge image not found: {image}")
            except APIError as e:
                raise RuntimeError(f"Docker error: {e}")

            container.reload()
            port_map = {}
            for internal, mappings in (container.attrs["NetworkSettings"]["Ports"] or {}).items():
                if mappings:
                    port_map[internal] = int(mappings[0]["HostPort"])

            instance = Instance(
                user_id=user_id,
                challenge_id=challenge_id,
                container_id=container.id,
                flag=flag,
                network_id=network.id,
                port_map=port_map,
                expires_at=time.time() + timeout_seconds,
            )
            self.instances[key] = instance
            return instance

    def kill(self, user_id: str, challenge_id: str) -> bool:
        key = f"{user_id}:{challenge_id}"
        with self.lock:
            return self._kill_unsafe(key)

    def _kill_unsafe(self, key: str) -> bool:
        inst = self.instances.pop(key, None)
        if not inst:
            return False
        try:
            container = self.client.containers.get(inst.container_id)
            container.kill()
        except docker.errors.NotFound:
            pass
        return True

    def verify_flag(self, user_id: str, challenge_id: str, submitted: str) -> bool:
        key = f"{user_id}:{challenge_id}"
        inst = self.instances.get(key)
        if not inst:
            return False
        return secrets.compare_digest(submitted.strip(), inst.flag.strip())

    def reap_expired(self) -> int:
        now = time.time()
        with self.lock:
            expired = [k for k, i in self.instances.items() if i.expires_at < now]
            for k in expired:
                self._kill_unsafe(k)
            return len(expired)

    @staticmethod
    def _generate_flag(challenge_id: str, user_id: str) -> str:
        random_part = secrets.token_urlsafe(16)
        return f"ctf{{{challenge_id}_{user_id}_{random_part}}}"

    def run_reaper(self, interval: int = 30):
        """Background thread that reaps expired containers."""
        def loop():
            while True:
                try:
                    n = self.reap_expired()
                    if n:
                        print(f"[reaper] killed {n} expired instances")
                except Exception as e:
                    print(f"[reaper] error: {e}")
                time.sleep(interval)
        t = threading.Thread(target=loop, daemon=True, name="arena-reaper")
        t.start()
