# DeepSeek 问答服务

使用 FastAPI 将 DeepSeek 模型调用封装为 HTTP 接口，并通过 Docker 打包运行。支持输入校验、模型请求异常处理和服务端日志。

## 1. 功能与文件

| 文件 | 作用 |
| --- | --- |
| `server.py` | 定义接口、检查空问题、记录调用结果与耗时 |
| `chat.py` | 调用 DeepSeek API，解析答案并转换异常 |
| `client.py` | 在容器外调用本地接口的客户端示例 |
| `requirements.txt` | 固定 Python 依赖及其版本 |
| `Dockerfile` | 准备 Python 环境、安装依赖、复制代码并设置启动命令 |
| `.dockerignore` | 排除本机虚拟环境、缓存和本地配置等文件 |

当前 HTTP 接口每次发送 system 提示词和本次问题，属于单轮问答。虽然 `chat.py` 中有 `ChatSession` 类，但当前接口没有使用它保存多轮历史。

## 2. 运行条件

- Docker 客户端和服务端可正常连接，可用 `docker version` 检查。
- 可用的 DeepSeek API Key。
- 容器能够访问 DeepSeek API；构建时能够下载基础镜像和 Python 依赖。
- 本机 8000 端口可用。

当前 Dockerfile 使用 `python:3.12-slim`，实际检查过的容器 Python 版本为 3.12.16。运行容器不依赖宿主机的 `.venv`。

## 3. 构建镜像

在包含 Dockerfile、requirements.txt、server.py 和 chat.py 的项目目录执行：

```bash
docker build -t agent-api:v1 .
```

- `agent-api`：镜像名称；`v1`：镜像标签。
- 最后的 `.`：使用当前目录作为构建上下文。
- 构建时安装依赖并复制代码；此时不会启动 FastAPI。
- 镜像由 Docker 管理，不会在项目目录生成一个普通镜像文件。

查看构建结果：

```bash
docker image ls agent-api
```

## 4. 配置密钥并首次启动

下面的命令用于 Linux 的 Bash 或 Zsh 终端。

先隐藏输入 API Key：

```bash
read -r -s DEEPSEEK_API_KEY
```

粘贴密钥并按回车。输入时不显示字符是正常的。接着执行：

```bash
export DEEPSEEK_API_KEY
```

首次创建并在后台运行容器：

```bash
docker run -d \
  --name agent-api-container \
  -p 127.0.0.1:8000:8000 \
  -e DEEPSEEK_API_KEY \
  agent-api:v1
```

| 参数 | 含义 |
| --- | --- |
| `-d` | 在后台运行 |
| `--name agent-api-container` | 指定容器名称 |
| `-p 127.0.0.1:8000:8000` | 将本机回环地址的 8000 端口映射到容器的 8000 端口 |
| `-e DEEPSEEK_API_KEY` | 将当前终端的同名环境变量值传入新容器 |
| `agent-api:v1` | 创建容器所用的镜像 |

API Key 在运行时传入，不写进代码、Dockerfile 或镜像。不要提交真实密钥或将其输出到日志中。

本示例将新容器的端口限制在本机访问。已有容器实际可能绑定所有宿主机接口，以 `docker port agent-api-container` 的输出为准。

### 已经有同名容器时

先查看：

```bash
docker ps -a
```

如果 `agent-api-container` 已经存在且停止，使用：

```bash
docker start agent-api-container
```

如果已经运行，直接访问接口即可，不必重复执行 `docker run`。

`start` 会保留创建时的环境变量和端口配置，因此同一个已配置密钥的容器停止后再启动，不需要重新传入密钥。修改宿主机环境变量不会自动更新现有容器。

## 5. 接口与测试

服务启动后，打开：

- 健康检查：[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- 交互式接口文档：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

日志里的 `0.0.0.0:8000` 是容器内的监听地址。本机访问时使用端口映射对应的地址。

### GET /health

```bash
curl http://127.0.0.1:8000/health
```

预期返回 200：

```json
{"status": "OK"}
```

此接口只检查服务能够响应，不检查密钥有效性或模型网络连通性。

### POST /chat

在 /docs 中选择 POST /chat，点击 Try it out，输入问题后点击 Execute；也可以执行：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"你好"}'
```

成功时返回 200，响应结构如下，答案内容以实际模型返回为准：

```json
{"answer": "模型返回的答案"}
```

空白输入测试：

```bash
curl -i -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"   "}'
```

预期返回 400：

```json
{"detail": "问题不可为空"}
```

### 错误响应

| 状态码 | 当前处理的情况 |
| --- | --- |
| 400 | 问题为空字符串或全为空白 |
| 422 | 请求数据未通过模型校验，例如缺少 question 或传入 null |
| 503 | 容器中未设置 DEEPSEEK_API_KEY |
| 504 | 等待上游模型响应超时 |
| 502 | 上游连接或 HTTP 错误、响应解析失败、答案无效等 |

错误说明以代码中的 `HTTPException.detail` 为准。密钥存在但无效时，不属于“未设置密钥”，上游 HTTP 错误会按当前代码转换为 502。

## 6. 日志与容器管理

查看运行中的容器：

```bash
docker ps
```

查看全部容器，包括已停止的容器：

```bash
docker ps -a
```

查看最后 20 行日志：

```bash
docker logs --tail 20 agent-api-container
```

持续跟踪日志：

```bash
docker logs -f --tail 20 agent-api-container
```

在此日志跟踪命令中按 Ctrl+C，只退出日志查看，后台容器继续运行。日志可能包含同一个容器此前运行时的记录。

查看端口映射：

```bash
docker port agent-api-container
```

停止容器：

```bash
docker stop agent-api-container
```

启动已停止的容器：

```bash
docker start agent-api-container
```

在运行中的容器里检查 Python 版本和代码文件：

```bash
docker exec agent-api-container python --version
docker exec agent-api-container ls /app
```

正常日志会记录收到请求、模型调用成功及耗时；失败日志会记录错误状态、说明和耗时。当前应用日志输出到终端，由 Docker 的日志机制收集，应用没有额外配置日志文件。

## 7. 修改代码或更新密钥

Dockerfile 的 COPY 会把构建时的代码复制进镜像。本机文件修改后，已有镜像和容器里的副本不会自动更新。

更新步骤：

1. 修改并保存本机代码；如果更新密钥，先在当前终端重新输入并 export。
2. 重新构建镜像。
3. 停止旧容器，删除旧容器实例。
4. 使用新镜像和所需环境变量重新创建容器。

```bash
docker build -t agent-api:v1 .
docker stop agent-api-container
docker rm agent-api-container
docker run -d \
  --name agent-api-container \
  -p 127.0.0.1:8000:8000 \
  -e DEEPSEEK_API_KEY \
  agent-api:v1
```

删除容器会丢弃该实例可写层中的改动和容器日志，不删除本机项目源码或镜像。当前示例没有持久化业务数据；若以后加入数据库或文件存储，重建前需要另行处理数据持久化。

重新构建同名镜像不会更新旧容器；仅停止再启动旧容器也不会切换到新镜像。

## 8. 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| 提示容器名称已存在 | 用 docker ps -a 查看；启动现有容器，或按更新流程重建 |
| 提示端口已占用 | 检查本机 Uvicorn 或其他容器；新建容器时可改为 -p 127.0.0.1:8001:8000，随后访问 8001 |
| 启动后 docker ps 看不到容器 | 用 docker ps -a 查看状态，再查看 docker logs |
| /health 正常但 /chat 返回 503 | 检查创建容器时是否传入 DEEPSEEK_API_KEY |
| /chat 返回 502 或 504 | 查看错误日志，检查上游密钥、网络、服务响应或超时 |
| 修改代码后接口行为不变 | 确认重新构建镜像，并用新镜像重新创建容器 |
| 启动命令找不到 uvicorn | 检查 Dockerfile 中的拼写，以及 requirements.txt 是否包含 uvicorn |

## 9. 验证记录与当前边界

已在学习过程中手动验证：

- 容器重启后 /health 返回 200。
- 容器重启后正常 /chat 返回 200，并取得模型答案。
- 容器重启后空白问题返回 400。
- 正常与空白请求日志可用。
- 在此前本地服务测试中，主动抛出 Timeout 可触发 504 和错误日志；删除模拟代码后恢复 200。
- docker exec 可查看 Python 3.12.16 和 /app 中的项目文件。
- requirements.txt 已从可运行的容器导出固定版本；导出后的新构建需再检查是否成功。

当前 HTTP 接口没有多用户会话、登录鉴权、数据库持久化或工具调用功能。本项目用于练习模型 API 服务化与 Docker 运行，后续再逐步扩展。

## 10. 官方参考

- [FastAPI：Docker 容器部署](https://fastapi.tiangolo.com/deployment/docker/)
- [Docker：创建并运行容器](https://docs.docker.com/reference/cli/docker/container/run/)
- [Docker：启动已有容器](https://docs.docker.com/reference/cli/docker/container/start/)

