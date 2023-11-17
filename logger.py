
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

def get_logger(name='ip'):
    logger = logging.getLogger(name=name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    # 输出到屏幕
    formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 输出到日志文件
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_file = os.path.join(log_dir, "check_aws_ips.log")

    # 限制日志最多保存7天
    file_handler = TimedRotatingFileHandler(log_file, when='D', interval=1, backupCount=7)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
