#!/usr/bin/env -S uv run
import argparse
import asyncio
import inspect
import logging
import shlex
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import yaml
from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).parent
WORK_DIR = Path.cwd()

parser = argparse.ArgumentParser(
    prog="mcp-bridge",
    description="tools.yaml で定義したコマンドを MCP Tool として公開する HTTP サーバー。",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--config", type=Path, default=WORK_DIR / "tools.yaml",
    metavar="FILE",
    help="ツール定義 YAML ファイル",
)
parser.add_argument(
    "--sandbox", type=Path, default=None,
    metavar="FILE",
    help="sandbox-exec に渡す Seatbelt プロファイル (省略時はサンドボックスなし)",
)
parser.add_argument(
    "--port", type=int, default=8000,
    help="リスンするポート番号",
)
parser.add_argument(
    "--allowed-hosts", dest="allowed_hosts", nargs="+", default=[],
    metavar="HOST",
    help="Host ヘッダとして許可する追加ホスト名 (例: host.docker.internal)",
)
args, _ = parser.parse_known_args()

CONFIG_PATH: Path = args.config
SANDBOX_PROFILE: Path = args.sandbox
PORT: int = args.port
ALLOWED_HOSTS: list[str] = args.allowed_hosts

from mcp.server.fastmcp.server import TransportSecuritySettings


def build_transport_security(extra_hosts: list[str]) -> TransportSecuritySettings | None:
    if not extra_hosts:
        return None
    defaults = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    extras = [h if ":" in h else f"{h}:*" for h in extra_hosts]
    return TransportSecuritySettings(allowed_hosts=defaults + extras)


mcp = FastMCP("mcp-bridge", port=PORT, transport_security=build_transport_security(ALLOWED_HOSTS))

TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


async def run_shell(command: str) -> str:
    if SANDBOX_PROFILE:
        cmd = ["sandbox-exec", "-f", str(SANDBOX_PROFILE), "sh", "-c", command]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORK_DIR,
        )
    else:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORK_DIR,
        )
    stdout, stderr = await proc.communicate()
    output = stdout.decode()
    if stderr:
        output += "\n" + stderr.decode()
    return output


def make_tool_func(tool_def: dict):
    name = tool_def["name"]
    description = tool_def.get("description", "")
    command_template = tool_def["command"]
    params = tool_def.get("parameters", [])

    sig_params = []
    for p in params:
        ptype = TYPE_MAP.get(p.get("type", "string"), str)
        default = p.get("default", inspect.Parameter.empty)
        sig_params.append(
            inspect.Parameter(
                p["name"],
                kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=ptype,
                default=default,
            )
        )

    async def tool_func(**kwargs) -> str:
        safe_values = {k: shlex.quote(str(v)) for k, v in kwargs.items()}
        command = command_template.format(**safe_values)
        return await run_shell(command)

    tool_func.__name__ = name
    tool_func.__doc__ = description
    tool_func.__signature__ = inspect.Signature(sig_params, return_annotation=str)

    return tool_func


def load_tools():
    if not CONFIG_PATH.exists():
        parser.error(
            f"設定ファイルが見つかりません: {CONFIG_PATH}\n"
            "  tools.yaml を作成するか、--config でパスを指定してください。\n"
            "  例: mcp-bridge --config /path/to/tools.yaml"
        )

    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for tool_def in config.get("tools", []):
        func = make_tool_func(tool_def)
        mcp.add_tool(func, name=tool_def["name"], description=tool_def.get("description", ""))


load_tools()


def run():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    run()
