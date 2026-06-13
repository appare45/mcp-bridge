import inspect
import shlex
import subprocess
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-bridge")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "tools.yaml"

TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def run_shell(command: str) -> str:
    """シェルコマンドを実行して標準出力/標準エラーを返す"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=BASE_DIR)
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
    return output


def make_tool_func(tool_def: dict):
    """YAMLのツール定義から、安全にコマンドを実行する関数を動的に生成する"""
    name = tool_def["name"]
    description = tool_def.get("description", "")
    command_template = tool_def["command"]
    params = tool_def.get("parameters", [])

    # 動的に関数のシグネチャ(パラメータ名・型・デフォルト値)を構築する
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
        # 各値をシェルエスケープしてコマンドテンプレートに埋め込む
        safe_values = {k: shlex.quote(str(v)) for k, v in kwargs.items()}
        command = command_template.format(**safe_values)
        return run_shell(command)

    tool_func.__name__ = name
    tool_func.__doc__ = description
    tool_func.__signature__ = inspect.Signature(sig_params, return_annotation=str)

    return tool_func


def load_tools():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for tool_def in config.get("tools", []):
        func = make_tool_func(tool_def)
        mcp.add_tool(func, name=tool_def["name"], description=tool_def.get("description", ""))


load_tools()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
