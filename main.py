#!/usr/bin/env -S uv run
import argparse
import inspect
import logging
import shlex
import subprocess
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
args, _ = parser.parse_known_args()

CONFIG_PATH: Path = args.config
SANDBOX_PROFILE: Path = args.sandbox
PORT: int = args.port

mcp = FastMCP("mcp-bridge")

TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def run_shell(command: str) -> str:
    if SANDBOX_PROFILE:
        cmd = ["sandbox-exec", "-f", str(SANDBOX_PROFILE), "sh", "-c", command]
    else:
        cmd = ["sh", "-c", command]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=WORK_DIR)
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
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

    def tool_func(**kwargs) -> str:
        safe_values = {k: shlex.quote(str(v)) for k, v in kwargs.items()}
        command = command_template.format(**safe_values)
        return run_shell(command)

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
    mcp.run(transport="streamable-http", port=PORT)


if __name__ == "__main__":
    run()
