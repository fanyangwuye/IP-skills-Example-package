FROM python:3.11-slim

# 系统依赖：ffmpeg（视频拼接/音频处理需要），其余为 Pillow 运行所需
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目
COPY . .

# 输出目录默认指向容器内 /app/outputs；云端部署时用环境变量覆盖为持久存储/挂载卷
ENV IP_SKILLS_OUTPUT_ROOT=/app/outputs
RUN mkdir -p /app/outputs /app/logs

# API key 等敏感配置通过运行时环境变量注入，不写入镜像
# 例：docker run -e IMAGE_API_KEY=... -e VIDEO_API_KEY=... -e IP_SKILLS_OUTPUT_ROOT=/data/outputs ...

# 默认无常驻进程：这是 skills 库，由 agent import 调用。
# 如需自检，可运行：python -c "import sys; sys.path.insert(0,'skills/ip-video-skill/scripts'); import video_handoff; print('ok')"
CMD ["python", "-c", "print('ip-skills ready; import the skill scripts from an agent')"]
