# 基于python3.10 alpine
FROM python:3.10-alpine
# 只将当前文件夹下的requirements.txt 放进容器
COPY requirements.txt /requirements.txt
# 设置工作目录
WORKDIR /app
# 使用清华源安装 pip 包
RUN pip install -r /requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
# 容器启动时运行main.py
CMD ["python", "main.py"]
