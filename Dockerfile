#设置容器中的python版本
FROM python:3.12-slim
#设置工作目录，不存在时会创建
WORKDIR /app
#复制依赖清单
COPY requirements.txt ./
#安装依赖，把清单中的包安装到镜像,--no-cache-dir表示不保留pip的下载缓存，减少镜像占用
RUN python -m pip install --no-cache-dir -r requirements.txt
#复制服务代码
COPY server.py chat.py ./
#设置启动命令
CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000"]
