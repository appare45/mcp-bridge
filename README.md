# mcp-bridge

YAML設定ファイル(`tools.yaml`)を読み込んで、定義されたコマンドを
MCP Toolとして自動公開するHTTP TransportのMCPサーバー。

## ユースケース: DevContainerからホストのコマンドを安全に呼び出す

DevContainerやDockerコンテナ内で動くAIエージェント(Claude Code など)は、
デフォルトではホストOSのコマンドを実行できません。

mcp-bridgeを**ホスト側**で起動し、コンテナ側のエージェントからHTTP経由でMCPサーバーに接続することで、
**`tools.yaml`に列挙したコマンドだけ**をエージェントに許可できます。

```
┌─────────────────────────────────┐       ┌──────────────────────────┐
│  Host                           │       │  DevContainer            │
│                                 │       │                          │
│  mcp-bridge --sandbox sandbox.sb│◀─────▶│  AI Agent (Claude Code)  │
│  (http://localhost:8000/mcp)    │  MCP  │                          │
│                                 │       │                          │
│  ホストのコマンドを制限付きで実行 │       │  tools.yaml の範囲でのみ  │
│                                 │       │  ホストコマンドを呼べる   │
└─────────────────────────────────┘       └──────────────────────────┘
```

`tools.yaml` で公開するコマンドを絞り込み、`--sandbox` でsandbox-execによる
Seatbeltプロファイルを適用することで、意図しないコマンドの実行を防げます。

## インストール

```bash
uv tool install git+https://github.com/appare45/mcp-bridge
```

### 開発中に直接実行する場合

```bash
uv sync
uv run main.py
```

## 起動

```bash
# サンドボックスなし
mcp-bridge --config /path/to/tools.yaml

# ポート指定
mcp-bridge --config /path/to/tools.yaml --port 9000

# Seatbeltサンドボックスあり (macOS)
mcp-bridge --config /path/to/tools.yaml --sandbox /path/to/sandbox.sb
```

`http://127.0.0.1:8000/mcp` でリスンします。

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

### 例: `import Darwin` を使う Swift パッケージの開発

`import Darwin` など macOS 固有の API を使う Swift パッケージは、Linux コンテナ内ではビルドできません。
mcp-bridge をホストで動かすことで、コンテナ内のエージェントがホストの `swift build` を呼び出せます。

```yaml
tools:
  - name: swift_build
    description: ホスト上の Swift パッケージをビルドする (import Darwin など macOS 専用 API を含む場合に使用)
    command: "swift build --package-path {path}"
    parameters:
      - name: path
        type: string
        description: Package.swift があるディレクトリのパス
```

## クライアント設定例

ホスト側の起動（`host.docker.internal` を許可）：

```bash
mcp-bridge --config /path/to/tools.yaml --allowed-hosts host.docker.internal
```

プロジェクトルートの `.mcp.json`：

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "type": "http",
      "url": "http://host.docker.internal:8000/mcp"
    }
  }
}
```

> **Linux の場合** `host.docker.internal` が解決できないことがあります。
> その場合は `docker run --add-host=host-gateway:host-gateway` でホストのIPを注入するか、
> ブリッジネットワークのゲートウェイIP（通常 `172.17.0.1`）を直接指定してください。
