
## 本地构建
如果看到这里，PR 已经合并，可以跳过自行构建本地插件使用
### 打包
```shell
# 打包命令
rm -f schemarag-0.1.7.difypkg && docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work schemarag-pack plugin package . -o "schemarag-$(grep '^version:' manifest.yaml | head -1 | cut -d' ' -f2).difypkg

```
```shell
# 打包文件
# 本地打 .difypkg（与 CI 相同 CLI）。用法见文件末尾注释。
# 无法拉取 bookworm 时可：--build-arg BASE_IMAGE=python:3.12-slim
ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE} AS packer

ARG DIFY_PLUGIN_CLI_VERSION=0.0.6
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q "https://github.com/langgenius/dify-plugin-daemon/releases/download/${DIFY_PLUGIN_CLI_VERSION}/dify-plugin-linux-amd64" \
        -O /usr/local/bin/dify-plugin \
    && chmod +x /usr/local/bin/dify-plugin

WORKDIR /work
ENTRYPOINT ["dify-plugin"]

# 默认仅作占位；实际请挂载仓库根目录并覆盖参数，例如：
#   docker build --platform linux/amd64 -f Dockerfile.pack -t schemarag-pack .
#   docker build --platform linux/amd64 --build-arg BASE_IMAGE=python:3.12-slim -f Dockerfile.pack -t schemarag-pack .
#   docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work schemarag-pack \
#     plugin package . -o "$(grep '^name:' manifest.yaml | cut -d' ' -f2)-$(grep '^version:' manifest.yaml | head -1 | cut -d' ' -f2).difypkg"
CMD ["plugin", "package", "."]

```


### 本地插件安装

通过Dockerfile.pack打包，在 dify compose（/usr/local/dify/docker/ 根据自己实际情况来） 目录修改 .env 文件

```shell
# 修改文件值
FORCE_VERIFYING_SIGNATURE=false
# 重启dify
docker compose down
docker compose up -d
```

## 部署后安装DM驱动


### DM 驱动安装流程

适用于 **已在运行的 Dify `plugin_daemon` 容器**（示例名 `docker-plugin_daemon-1`）内，为已部署的 SchemaRAG 插件补齐达梦客户端与 Python 驱动。流程与仓库内 `Dockerfile.dameng` 一致：**从 ISO 静默解出 `Install.tar.gz` 到 `/opt/dm8`**，再在**插件自带的 `.venv`** 里源码安装 `dmPython`、`dmSQLAlchemy`，避免仅用 pip wheel 时缺少 DPI/加密相关模块。

### 安装介质

从 [达梦下载页](https://www.dameng.com/download/) 下载 Linux x86_64、与宿主/镜像匹配的包（如 `dm8_*_x86_Ubuntu22_64.zip`），解压得到 `.iso`。将介质拷入容器后再解包，例如：
### 运行命令-准备
```shell
# cp 命令
docker cp "/home/dm8_20260401_x86_Ubuntu22_64.zip" docker-plugin_daemon-1:/tmp/dm8.zip

# exec 进入容器
docker exec -it docker-plugin_daemon-1 /bin/bash

# 更新软件源并安装 unzip
apt-get update && apt-get install -y unzip

# 静默解压 dm8.zip 到 /tmp 目录
unzip -q /tmp/dm8.zip -d /tmp/

# 安装相关依赖（根据实际情况来） 如果没报错就不执行，报错了缺什么就补什么
apt-get install -y \
    libarchive-tools \
    gzip \
    tar \
    unzip \
    libaio-dev \
    libncurses6
    
mkdir -p /tmp/dm8-iso /opt/dm8 

tar -xf /tmp/dm8_20260401_x86_Ubuntu22_64.iso -C /tmp/dm8-iso

test -f /tmp/dm8-iso/DMInstall.bin

python3 -c "from pathlib import Path; b=Path('/tmp/dm8-iso/DMInstall.bin').read_bytes(); off=b.find(b'\x1f\x8b\x08'); assert off!=-1, 'gzip header not found'; Path('/tmp/Install.tar.gz').write_bytes(b[off:]); print('payload_offset', off, 'payload_size', len(b)-off)"

ls -lh /tmp/Install.tar.gz

mkdir -p /opt/dm8

gzip -dc /tmp/Install.tar.gz | tar -xf - -C /opt/dm8

# 检查结果
ls -lah /opt/dm8
ls -lah /opt/dm8/source
ls -lah /opt/dm8/source/drivers/python
```
### 运行命令-安装
```shell
# 安装依赖
# VENV_PY 使用pa -aux找到真正运行插件位置，修改配置
# 第一次报错不要紧 "$VENV_PY" -c "import sys; print(sys.version, sys.executable)" 是这里测试环境的时候
# 生产环境 Shell 脚本必备，能避免 90% 的隐形 bug
set -euo pipefail
VENV_PY=/app/storage/cwd/joto/schemarag-0.1.7@b1d24ddfccc76c0054ff50ada5fe93f54e1cc5ddd3a46fbe0bfd48c346eb3777/.venv/bin/python
export DM_HOME=/opt/dm8/source
export LD_LIBRARY_PATH=/opt/dm8/source/bin:${LD_LIBRARY_PATH:-}
export PATH=/opt/dm8/source/bin:${PATH}


# 第一步：确认解释器
"$VENV_PY" -c "import sys; print(sys.version, sys.executable)"

# 第二步：修复 pip（确保可用）
"$VENV_PY" -m ensurepip --default-pip 2>/dev/null || true
"$VENV_PY" -m pip install --upgrade pip setuptools wheel

# 第三步：安装 dmPython（setup.py 路线）
cd /opt/dm8/source/drivers/python/dmPython
"$VENV_PY" -c "import dmPython; print('dmPython OK')"
"$VENV_PY" setup.py install

# 第四步：安装 dmSQLAlchemy
cd /opt/dm8/source/drivers/python/dmSQLAlchemy/dmSQLAlchemy2.0
"$VENV_PY" setup.py install

```
### 运行命令-测试
````shell

# 测试启动（可以忽略）

cd /app/storage/cwd/joto/schemarag-0.1.7@b1d24ddfccc76c0054ff50ada5fe93f54e1cc5ddd3a46fbe0bfd48c346eb3777
"$VENV_PY" -m main
```

```java
# 测试连接（可以忽略）

VENV_PY=/app/storage/cwd/joto/schemarag-0.1.7@b1d24ddfccc76c0054ff50ada5fe93f54e1cc5ddd3a46fbe0bfd48c346eb3777/.venv/bin/python
"$VENV_PY" - <<'PY'
from sqlalchemy import create_engine, text
import dmSQLAlchemy

engine = create_engine("dm+dmPython://SYSDBA:123abc%21%40%23@127.0.0.1:5236")
with engine.connect() as conn:
    conn.exec_driver_sql('ALTER SESSION SET CURRENT_SCHEMA = "TEST_DB"')
    print(conn.execute(text("select sys_context('USERENV','CURRENT_SCHEMA') from dual")).fetchall())
    print(conn.execute(text("select 1 as ok from dual")).fetchall())
PY

````

### 持久化环境
```
# 测试都成功后，可以持久化时可写入docker compose 文件插件进程所用环境，保证插件子进程继承上述变量。记得重启dify（只需要新增env中的几个环境即可）
plugin_daemon:
    image: langgenius/dify-plugin-daemon:0.4.1-local
    restart: always
    environment:
      DM_HOME: /opt/dm8/source
      LD_LIBRARY_PATH: /opt/dm8/source/bin:/opt/dm8/source/bin/dependencies
      PATH: /opt/dm8/source/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### 注意事项

- 达梦客户端驱动面向 **Linux / Windows**；**macOS 上无法连接达梦**（与本项目说明一致）。
- `DM_HOME` 必须指向 **`/opt/dm8/source`**；`LD_LIBRARY_PATH` 需包含 `bin` 与 `bin/dependencies`。
- 确保能访问达梦数据库服务（网络、账号、端口如 5236）。
