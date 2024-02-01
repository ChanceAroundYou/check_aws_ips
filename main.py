import argparse
import configparser

import requests
import boto3
from agh import Adguardhome
from logger import get_logger
from ping import ping_ip

LOGGER = get_logger()

def change_ip(client, ip_name, instance_name, old_ip, no_release=False):
    region_name = client.meta.region_name
    if not no_release:
        client.release_static_ip(staticIpName=ip_name)
    client.allocate_static_ip(staticIpName=ip_name)
    client.attach_static_ip(staticIpName=ip_name, instanceName=instance_name)
    new_ip = client.get_instance(instanceName=instance_name)["instance"][
        "publicIpAddress"
    ]
    LOGGER.warning(
        f"IP地址已更换, {region_name}的服务器{instance_name}, {ip_name}从{old_ip}更换至{new_ip}"
    )
    after_change_ip(client, new_ip, instance_name)
    return new_ip

def after_change_ip(client, new_ip_addr, instance_name):
    LOGGER.info(f"检查更换后IP")

    if not ping_ip(new_ip_addr):
        LOGGER.error(f"更换后IP异常, 重启服务器")
        client.reboot_instance(instanceName=instance_name)

def update_rewrite(client, agh, instance_name, ip_addr):
    instance = client.get_instance(instanceName=instance_name)
    domain = instance["instance"]["tags"][0]["key"]
    LOGGER.info(f"添改rewrite: {domain} -> {ip_addr}")
    agh.add_or_update_rewrite(domain, ip_addr)

def check_region(client: boto3.Session.client, agh, force=False):
    ip_list = client.get_static_ips()["staticIps"]    
    
    for ip in ip_list:
        ip_addr = ip["ipAddress"]
        ip_name = ip["name"]

        if not ip["isAttached"]:
            LOGGER.error(f"IP{ip_name}: {ip_addr}未附着到服务器, 删除")
            client.release_static_ip(staticIpName=ip_name)

    checked_ip_list = []
    instance_list = client.get_instances()['instances']
    for instance in instance_list:
        instance_name = instance["name"]
        ip_name = instance["tags"][0]["key"]
        ip_addr = instance["publicIpAddress"]
        is_static_ip = instance['isStaticIp']

        if not is_static_ip:
            LOGGER.warning(f"服务器{instance_name}不是静态IP")
            ip_addr = change_ip(client, ip_name, instance_name, ip_addr, no_release=True)

        elif force:
            LOGGER.warning(f"强制更换{instance_name}:{ip_addr}")
            ip_addr = change_ip(client, ip_name, instance_name, ip_addr)

        elif not ping_ip(ip_addr):
            LOGGER.warning(f"服务器{instance_name}的IP{ip_addr}异常")
            ip_addr = change_ip(client, ip_name, instance_name, ip_addr)
        else:
            LOGGER.info(f"服务器{instance_name}的IP{ip_addr}正常")
            continue

        update_rewrite(client, agh, instance_name, ip_addr)
        checked_ip_list.append(ip_addr)
        
    # checked_ip_list = [ip["ipAddress"] for ip in client.get_static_ips()["staticIps"]]
    return checked_ip_list


def update_checked_ip_list_to_clash(checked_ip_list):
    url = 'https://openwrt.cheerl.space:9080/cgi-bin/update_clash'
    data = ",".join(checked_ip_list)
    LOGGER.info(data)
    response = requests.post(url, data=data, verify=False)
    
    if response.text[0] == '1':
        LOGGER.warning("更新clash配置")

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


def main():
    config = configparser.ConfigParser()
    config.read("config.ini")
    regions = config["DEFAULT"]["AWS_REGIONS"]
    key = config["DEFAULT"]["AWS_ACCESS_KEY_ID"]
    secret = config["DEFAULT"]["AWS_SECRET_ACCESS_KEY"]
    agh_name = config["DEFAULT"]["AGH_NAME"]
    agh_password = config["DEFAULT"]["AGH_PASSWORD"]
    agh_base_url = config["DEFAULT"]["AGH_BASE_URL"]

    parser = argparse.ArgumentParser(description="检查AWS服务器IP是否正常")
    parser.add_argument("--force", action="store_true", help="是否强制更换IP")
    parser.add_argument("--regions", default=regions, help="需要检查的区域, 以逗号分隔")
    parser.add_argument("--key", default=key, help="AWS_ACCESS_KEY_ID")
    parser.add_argument("--secret", default=secret, help="AWS_SECRET_ACCESS_KEY")
    args = parser.parse_args()

    agh = Adguardhome(agh_name, agh_password, agh_base_url)

    checked_ip_list = []
    for region_name in args.regions.split(","):
        LOGGER.info(f"检查区域{region_name}")
        client = boto3.client(
            "lightsail",
            aws_access_key_id=args.key,
            aws_secret_access_key=args.secret,
            region_name=region_name,
        )
        checked_ip_list += check_region(client, agh, args.force)
    
    if checked_ip_list:
        update_checked_ip_list_to_clash(checked_ip_list)

    LOGGER.info("结束")

if __name__ == "__main__":
    main()
