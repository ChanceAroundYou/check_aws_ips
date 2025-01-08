import configparser
import os

import click
import requests
from loguru import logger

from agh import Adguardhome
from aliyundns import AliyunDNS
from lightsail import check_lightsail
from gist import Gist

config = configparser.ConfigParser()
config.read("config.ini")
default = config["DEFAULT"]
rule_aws_path = 'aws.yaml'

def update_ips_to_clash(updated_ips):
    if not any([domain_info['changed'] for domain_info in updated_ips.values()]):
        return

    logger.warning("更新clash配置")

    with open(rule_aws_path, "w") as f:
        f.write('payload:\n')
        for _, domain_info in updated_ips.items():
            f.write(f"  - IP-CIDR,{domain_info['ip']}/32\n")

    # url = "http://openwrt.cheerl.space/cgi-bin/update_clash"
    # data = ",".join(updated_ips.keys())
    # response = requests.post(url, data=data, verify=False)
    # logger.info(response.text)
    
    # if response.text[0] == "1":
    # logger.warning("更新clash配置")
    os.system('/usr/bin/scp aws.yaml router:/etc/openclash/rule_provider/AWS')

    headers = {"authorization": "Bearer 123456", "content-type": "application/json"}
    rule_url = 'http://openwrt.xiaokubao.space:9090/providers/rules/AWS'
    response = requests.put(rule_url, headers=headers)
    logger.info(response.text)

    reload_url = "http://openwrt.xiaokubao.space:9090/configs?force=true"
    payload = {"path": "", "payload": ""}
    response = requests.put(reload_url, headers=headers, json=payload)
    logger.info(response.text)


def update_ips_to_agh(agh, updated_ips):
    for domain, domain_info in updated_ips.items():
        if domain_info['changed']:
            logger.warning(f"修改AGH rewrite {domain} -> {domain_info['ip']}")
            agh.add_or_update_rewrite(domain, domain_info['ip'])


def update_ips_to_aliyun(dns, updated_ips):
    for domain, domain_info in updated_ips.items():
        if domain_info['changed']:
            logger.warning(f"更改AliYunDNS {domain} -> {domain_info['ip']}")
            dns.add_or_update_domain_record(domain.split('.')[0], domain_info['ip'])
            
def update_ips_to_gist(gist_api: Gist, gist_id, updated_ips):
    for domain, domain_info in updated_ips.items():
        if domain_info['changed']:
            logger.warning(f"更改Gist {domain} -> {domain_info['ip']}")
            gist_api.update_gist_content(file_name=domain, gist_id=gist_id, content=domain_info['ip'])

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
@click.option('--gist_token', default=default.get("GIST_TOKEN"), help="Gist Token")
@click.option('--gist_id', default=default.get("GIST_ID"), help="Gist ID")
def main(
    log_path, agh_name, agh_password, agh_base_url,
    aliyun_key, aliyun_secret, aliyun_domain,
    aws_key, aws_secret, regions, force,
    gist_token, gist_id
    ):
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)
    logger.add(log_path, rotation="23:59", retention="7 days", level="INFO")

    agh = Adguardhome(agh_name, agh_password, agh_base_url)
    dns = AliyunDNS(aliyun_key, aliyun_secret, aliyun_domain)
    gist_api = Gist(gist_token)

    updated_ips = check_lightsail(aws_key, aws_secret, regions, force)
    now_ips = agh.get_rewrite_dict()
    
    for domain, domain_info in updated_ips.items():
        if now_ips.get(domain, '') != domain_info['ip']:
            updated_ips[domain]['changed'] = True

    update_ips_to_gist(gist_api, gist_id, updated_ips)
    update_ips_to_aliyun(dns, updated_ips)
    update_ips_to_agh(agh, updated_ips)
    update_ips_to_clash(updated_ips)

    logger.info("结束")

if __name__ == '__main__':
    main()
    # updated_ips = {
    #     'aws.cheer.space': {
    #         'ip': '3.0.216.251',
    #         'changed': True
    #     }
    # }
    # update_ips_to_clash(updated_ips)
