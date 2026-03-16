import configparser
import os

import click
import requests
import retry
from loguru import logger

from agh import Adguardhome
from ec2 import check_ec2
from gist import Gist

config = configparser.ConfigParser()
config.read("config.ini")
default = config["DEFAULT"]

RULE_PATH = "aws.yaml"
DEFAULT_REGIONS=default.get("AWS_REGIONS")
DEFAULT_AWS_KEY=default.get("AWS_ACCESS_KEY_ID")
DEFAULT_AWS_SECRET=default.get("AWS_SECRET_ACCESS_KEY")
DEFAULT_AGH_NAME=default.get("AGH_NAME")
DEFAULT_AGH_PASSWORD=default.get("AGH_PASSWORD")
DEFAULT_AGH_BASE_URL=default.get("AGH_BASE_URL")
DEFAULT_DOMAIN=default.get("DOMAIN")
DEFAULT_LOG_PATH=default.get("LOG_PATH")
DEFAULT_GIST_TOKEN=default.get("GIST_TOKEN")
DEFAULT_GIST_ID=default.get("GIST_ID")


def update_ips_to_clash(updated_ips):
    if not any([domain_info["changed"] for domain_info in updated_ips.values()]):
        return

    logger.warning("更新clash配置")

    with open(RULE_PATH, "w") as f:
        f.write("payload:\n")
        for _, domain_info in updated_ips.items():
            f.write(f"  - IP-CIDR,{domain_info['ip']}/32\n")

    # url = "http://openwrt.cheerl.space/cgi-bin/update_clash"
    # data = ",".join(updated_ips.keys())
    # response = requests.post(url, data=data, verify=False)
    # logger.info(response.text)

    # if response.text[0] == "1":
    # logger.warning("更新clash配置")
    os.system("/usr/bin/scp aws.yaml router:/etc/openclash/rule_provider/AWS")

    headers = {"authorization": "Bearer Xkb111717!", "content-type": "application/json"}
    rule_url = "http://openwrt.xiaokubao.space:9090/providers/rules/AWS"
    response = requests.put(rule_url, headers=headers)
    logger.info(response.text)

    reload_url = "http://openwrt.xiaokubao.space:9090/configs?force=true"
    payload = {"path": "", "payload": ""}
    response = requests.put(reload_url, headers=headers, json=payload)
    logger.info(response.text)


@retry.retry(tries=3, delay=5)
def update_ips_to_agh(agh, updated_ips):
    for domain, domain_info in updated_ips.items():
        if domain_info["changed"]:
            logger.warning(f"修改AGH rewrite {domain} -> {domain_info['ip']}")
            agh.add_or_update_rewrite(domain, domain_info["ip"])


# @retry.retry(tries=3, delay=5)
# def update_ips_to_aliyun(dns, updated_ips):
#     for domain, domain_info in updated_ips.items():
#         if domain_info["changed"]:
#             logger.warning(f"更改AliYunDNS {domain} -> {domain_info['ip']}")
#             dns.add_or_update_domain_record(domain.split(".")[0], domain_info["ip"])


@retry.retry(tries=3, delay=5)
def update_ips_to_gist(gist_api: Gist, gist_id, updated_ips):
    for domain, domain_info in updated_ips.items():
        # if domain_info['changed']:
        logger.warning(f"更改Gist {domain} -> {domain_info['ip']}")
        gist_api.update_gist_content(
            file_name=domain, gist_id=gist_id, content=domain_info["ip"]
        )


@logger.catch()
@click.command()
@click.option("--force", type=bool, is_flag=True, help="是否强制重启实例")
@click.option("--regions", default=DEFAULT_REGIONS, help="需要检查的区域, 以逗号分隔")
@click.option("--aws_key", default=DEFAULT_AWS_KEY, help="AWS KEY")
@click.option("--aws_secret", default=DEFAULT_AWS_SECRET, help="AWS SECRET")
@click.option("--agh_name", default=DEFAULT_AGH_NAME, help="Adguardhome用户名")
@click.option("--agh_password", default=DEFAULT_AGH_PASSWORD, help="Adguardhome密码")
@click.option("--agh_base_url", default=DEFAULT_AGH_BASE_URL, help="Adguardhome地址")
# @click.option("--aliyun_key", default=default.get("ALIYUN_KEY"), help="阿里云AccessKey")
# @click.option("--aliyun_secret", default=default.get("ALIYUN_SECRET"), help="阿里云AccessSecret")
@click.option("--domain", default=DEFAULT_DOMAIN, help="阿里云域名")
@click.option("--log_path", default=DEFAULT_LOG_PATH, help="日志路径")
@click.option("--gist_token", default=DEFAULT_GIST_TOKEN, help="Gist Token")
@click.option("--gist_id", default=DEFAULT_GIST_ID, help="Gist ID")
def main(
    log_path,
    agh_name,
    agh_password,
    agh_base_url,
    # aliyun_key, aliyun_secret,
    aws_key,
    aws_secret,
    regions,
    domain,
    force,
    gist_token,
    gist_id,
):
    log_dir = os.path.dirname(log_path)
    os.makedirs(log_dir, exist_ok=True)
    logger.add(log_path, rotation="23:59", retention="7 days", level="INFO")

    agh = Adguardhome(agh_name, agh_password, agh_base_url)
    gist_api = Gist(gist_token)

    updated_ips = check_ec2(aws_key, aws_secret, regions, force)
    now_ips = agh.get_rewrite_dict()

    for domain, domain_info in updated_ips.items():
        if now_ips.get(domain, "") != domain_info["ip"]:
            updated_ips[domain]["changed"] = True

    # update_ips_to_aliyun(dns, updated_ips)
    update_ips_to_agh(agh, updated_ips)
    update_ips_to_clash(updated_ips)
    try:
        update_ips_to_gist(gist_api, gist_id, updated_ips)
    except Exception as e:
        logger.error(e)

    logger.info("结束")


if __name__ == "__main__":
    main()
