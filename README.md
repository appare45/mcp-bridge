# mcp-bridge

YAML設定ファイル(`tools.yaml`)を読み込んで、定義されたコマンドを
MCP Toolとして自動公開するHTTP TransportのMCPサーバー。

## セットアップ

```bash
uv sync
```

## 起動

```bash
uv run main.py
```

`http://127.0.0.1:8000/mcp` でリスンします。

## 実行ディレクトリ

各コマンドは、起動時のカレントディレクトリに関わらず、
常に `main.py` が置かれているディレクトリ(`mcp-server-demo/`)で実行されます。

## ツールの追加方法

`tools.yaml` に以下の形式でエントリを追加するだけです。コード変更は不要。

```yaml
tools:
  - name: ツール名
    description: ツールの説明(LLMに見せる説明文)
    command: "実行するコマンド {param1} {param2}"
    parameters:
      - name: param1
        type: string      # string / integer / number / boolean
        description: パラメータの説明
        default: デフォルト値   # 省略すると必須パラメータになる
      - name: param2
        type: integer
        default: 4
```

- `command` 内の `{param名}` がパラメータの値に置換されます
- 各値は `shlex.quote` でエスケープされ、コマンドに渡されます
- `parameters` を空配列 `[]` にすれば引数なしのツールになります

サーバーを再起動すると新しいツールが反映されます。

## サンプルツール (tools.yaml)

- `disk_usage`: `df -h`
- `list_files`: `ls -la <path>` (path省略可、デフォルト `.`)
- `current_time`: `date`
- `ping_host`: `ping -c <count> <host>` (count省略可、デフォルト 4)

## クライアント設定例

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```
