import configparser
import os

import click
import requests
from loguru import logger

from agh import Adguardhome
from aliyundns import AliyunDNS
from lightsail import check_lightsail

config = configparser.ConfigParser()
config.read("config.ini")
default = config["DEFAULT"]

def update_ips_to_clash(updated_ips):
    # if not updated_ips:
    #     return

    url = "https://openwrt.cheerl.space:9080/cgi-bin/update_clash"
    data = ",".join(updated_ips.keys())
    response = requests.post(url, data=data, verify=False)

    if response.text[0] == "1":
        logger.warning("更新clash配置")

        url = "http://openwrt.cheerl.space:9090/configs?force=true"
        headers = {"authorization": "Bearer 123456", "content-type": "application/json"}
        payload = {"path": "", "payload": ""}
        response = requests.put(url, headers=headers, json=payload)


def update_ips_to_agh(agh, updated_ips):
    for domain, ip_addr in updated_ips.items():
        logger.warning(f"修改AGH rewrite {domain} -> {ip_addr}")
        agh.add_or_update_rewrite(domain, ip_addr)


def update_ips_to_aliyun(dns, updated_ips):
    for domain, ip_addr in updated_ips.items():
        logger.warning(f"更改AliYunDNS {domain} -> {ip_addr}")
        dns.add_or_update_domain_record(domain, ip_addr)

@logger.catch()
@click.command()
@click.option("--force", type=bool, is_flag=True, help="是否强制更换IP")
@click.option("--regions", default=default.get("AWS_REGIONS"), help="需要检查的区域, 以逗号分隔")
@click.option("--aws_key", default=default.get("AWS_ACCESS_KEY_ID"), help="AWS KEY")
@click.option("--aws_secret", default=default.get("AWS_SECRET_ACCESS_KEY"), help="AWS SECRET")
@click.option("--agh_name", default=default.get("AGH_NAME"), help="Adguardhome用户名")
@click.option("--agh_password", default=default.get("AGH_PASSWORD"), help="Adguardhome密码")
@click.option("--agh_base_url", default=default.get("AGH_BASE_URL"), help="Adguardhome地址")
@click.option("--aliyun_key", default=default.get("ALIYUN_KEY"), help="阿里云AccessKey")
@click.option("--aliyun_secret", default=default.get("ALIYUN_SECRET"), help="阿里云AccessSecret")
@click.option("--aliyun_domain", default=default.get("ALIYUN_DOMAIN"), help="阿里云域名")
@click.option("--log_path", default=default.get("LOG_PATH"), help="日志路径")
def main(log_path, agh_name, agh_password, agh_base_url, aliyun_key, aliyun_secret, aliyun_domain, aws_key, aws_secret, regions, force):
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)
    logger.add(log_path, rotation="1 day", retention="7 days", level="INFO")

    agh = Adguardhome(agh_name, agh_password, agh_base_url)
    dns = AliyunDNS(aliyun_key, aliyun_secret, aliyun_domain)

    updated_ips = check_lightsail(aws_key, aws_secret, regions, force)

    update_ips_to_agh(agh, updated_ips)
    update_ips_to_aliyun(dns, updated_ips)
    update_ips_to_clash(updated_ips)

    logger.info("结束")

if __name__ == '__main__':
    main()