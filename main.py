import argparse
import configparser
import os

import requests
from loguru import logger

from agh import Adguardhome
from aliyundns import AliyunDNS
from lightsail import check_lightsail

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_path = os.path.join(log_dir, 'check.log')


def update_ips_to_clash(updated_ips):
    if not updated_ips:
        return

    url = 'https://openwrt.cheerl.space:9080/cgi-bin/update_clash'
    data = ",".join(updated_ips.keys())
    response = requests.post(url, data=data, verify=False)
    
    if response.text[0] == '1':
        logger.warning("更新clash配置")

        url = 'http://openwrt.cheerl.space:9090/configs?force=true'
        headers = {
            'authorization': 'Bearer 123456',
            'content-type': 'application/json'
        }
        payload = {
            'path': '',
            'payload': ''
        }
        response = requests.put(url, headers=headers, json=payload)

def update_ips_to_agh(agh, updated_ips):
    for domain, ip_addr in updated_ips.items():
        logger.warning(f"修改AGH rewrite: {domain} -> {ip_addr}")
        agh.add_or_update_rewrite(domain, ip_addr)

def update_ips_to_aliyun(dns, updated_ips):
    for domain, ip_addr in updated_ips.items():
        logger.warning(f"更改AliYunDNS {domain} -> {ip_addr}")
        dns.add_or_update_domain_record(domain, ip_addr)

@logger.catch()
def main():
    config = configparser.ConfigParser()
    config.read("config.ini")
    regions = config["DEFAULT"]["AWS_REGIONS"]
    key = config["DEFAULT"]["AWS_ACCESS_KEY_ID"]
    secret = config["DEFAULT"]["AWS_SECRET_ACCESS_KEY"]
    agh_name = config["DEFAULT"]["AGH_NAME"]
    agh_password = config["DEFAULT"]["AGH_PASSWORD"]
    agh_base_url = config["DEFAULT"]["AGH_BASE_URL"]
    aliyun_key = config["DEFAULT"]["ALIYUN_KEY"]
    aliyun_secret = config["DEFAULT"]["ALIYUN_SECRET"]
    aliyun_domain = config["DEFAULT"]["ALIYUN_DOMAIN"]

    parser = argparse.ArgumentParser(description="检查AWS服务器IP是否正常")
    parser.add_argument("--force", action="store_true", help="是否强制更换IP")
    parser.add_argument("--regions", default=regions, help="需要检查的区域, 以逗号分隔")
    parser.add_argument("--key", default=key, help="AWS_ACCESS_KEY_ID")
    parser.add_argument("--secret", default=secret, help="AWS_SECRET_ACCESS_KEY")
    parser.add_argument("--agh_name", default=agh_name, help="Adguardhome用户名")
    parser.add_argument("--agh_password", default=agh_password, help="Adguardhome密码")
    parser.add_argument("--agh_base_url", default=agh_base_url, help="Adguardhome地址")
    parser.add_argument("--aliyun_key", default=aliyun_key, help="阿里云AccessKey")
    parser.add_argument("--aliyun_secret", default=aliyun_secret, help="阿里云AccessSecret")
    parser.add_argument("--aliyun_domain", default=aliyun_domain, help="阿里云域名")
    args = parser.parse_args()

    logger.add(log_path, rotation="1 day", retention="7 days", level="INFO")

    agh = Adguardhome(args.agh_name, args.agh_password, args.agh_base_url)
    dns = AliyunDNS(args.aliyun_key, args.aliyun_secret, args.aliyun_domain)

    updated_ips = check_lightsail(args.key, args.secret, args.regions, args.force)

    update_ips_to_agh(agh, updated_ips)
    update_ips_to_aliyun(dns, updated_ips)
    update_ips_to_clash(updated_ips)

    logger.info("结束")

if __name__ == "__main__":
    main()
