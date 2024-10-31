import functools
import re
import subprocess
import time

from loguru import logger
from tcping import Ping

PING_TIME = 10

def ping_retry(num_retries, wait_time):
    def decorator(ping_func):
        @functools.wraps(ping_func)
        def wrapper(ip_addr, *args, **kwargs):
            for i in range(num_retries):
                if ping_func(ip_addr, *args, **kwargs):
                    return True
                else:
                    logger.warning(f"IP {ip_addr} 异常，等待{wait_time}秒后{i+1}/{num_retries}次重试")
                    time.sleep(wait_time)
            logger.error(f"IP {ip_addr} 无法连接")
            return False
        return wrapper
    return decorator

@ping_retry(num_retries=3, wait_time=5)
def wget_ip(ip_addr, domain='', ping_time=PING_TIME):
    logger.info(f"检查IP{ip_addr}")
    try:

        output = subprocess.check_output(['wget', '-O', '/dev/null', '-T', f'{ping_time}', f'https://{domain}/xui/']).decode('utf-8')
        logger.info('\n'+output)

        if "'/dev/null' saved" in output:
            logger.info(f"IP正常")
            return True
        else:
            logger.warning(f"IP异常")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Ping failed: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

@ping_retry(num_retries=3, wait_time=5)
def ping_ip(ip_addr, domain='', ping_time=PING_TIME):
    logger.info(f"检查IP{ip_addr}")
    try:
        # 执行系统的 ping 命令
        output = subprocess.check_output(['ping', '-c', f'{ping_time}', ip_addr]).decode('utf-8')
        logger.info('\n'+output)
        # 从输出结果中提取丢包率
        packet_loss = re.search(r'(\d+)% packet loss', output)
        avg_delay = re.search(r'min/avg/max(?:/mdev)* = (\d+\.*\d+)/(\d+\.*\d+)/(\d+\.*\d+)(?:/\d+\.*\d+)* ms', output)
        if packet_loss and avg_delay:
            loss_rate = float(packet_loss.group(1))
            avg_delay_value = float(avg_delay.group(2))

            logger.info(f"丢包率{loss_rate}%, 延迟{avg_delay_value}ms")
            if loss_rate < 40 and  5 < avg_delay_value < 500:
                logger.info(f"IP正常")
                return True

        logger.warning(f"IP异常")
        return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Ping failed: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return False

@ping_retry(num_retries=3, wait_time=5)
def tcpping_ip(ip_addr, domain='', ping_time=PING_TIME):
    logger.info(f"检查IP{ip_addr}")
    
    ping = Ping(ip_addr)
    ping.ping(ping_time)
    success_rate = ping.result.rows[0].success_rate

    if success_rate == "0.00%":
        logger.warning(f"IP异常, {success_rate}")
        return False
    else:
        logger.info(f"IP正常, {success_rate}")
        return True
    
def detect_ip(ip_addr, domain='', ping_time=PING_TIME):
    if domain in []:
        return wget_ip(ip_addr, domain, ping_time)
    else:
        return ping_ip(ip_addr, domain, ping_time)