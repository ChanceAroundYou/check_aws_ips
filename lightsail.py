import boto3
from loguru import logger

from ping import ping_ip


def change_ip(client, ip_name, instance_name, old_ip, no_release=False):
    region_name = client.meta.region_name
    if not no_release:
        client.release_static_ip(staticIpName=ip_name)
    client.allocate_static_ip(staticIpName=ip_name)
    client.attach_static_ip(staticIpName=ip_name, instanceName=instance_name)
    new_ip = client.get_instance(instanceName=instance_name)["instance"][
        "publicIpAddress"
    ]
    logger.warning(
        f"IP地址已更换, {region_name}的服务器{instance_name}, {ip_name}从{old_ip}更换至{new_ip}"
    )
    after_change_ip(client, new_ip, instance_name)
    return new_ip

def after_change_ip(client, new_ip_addr, instance_name):
    logger.info(f"检查更换后IP")

    if not ping_ip(new_ip_addr):
        logger.error(f"更换后IP异常, 重启服务器")
        client.reboot_instance(instanceName=instance_name)



def check_region(client: boto3.Session.client, force=False):
    ip_list = client.get_static_ips()["staticIps"]    
    
    for ip in ip_list:
        ip_addr = ip["ipAddress"]
        ip_name = ip["name"]

        if not ip["isAttached"]:
            logger.error(f"IP{ip_name}: {ip_addr}未附着到服务器, 删除")
            client.release_static_ip(staticIpName=ip_name)

    updated_ips = {}
    instance_list = client.get_instances()['instances']
    for instance in instance_list:
        instance_name = instance["name"]
        domain = instance["tags"][0]["key"]
        ip_addr = instance["publicIpAddress"]
        is_static_ip = instance['isStaticIp']

        if not is_static_ip:
            logger.warning(f"服务器{instance_name}不是静态IP")
            ip_addr = change_ip(client, domain, instance_name, ip_addr, no_release=True)

        elif force:
            logger.warning(f"强制更换{instance_name}:{ip_addr}")
            ip_addr = change_ip(client, domain, instance_name, ip_addr)

        elif not ping_ip(ip_addr):
            logger.warning(f"服务器{instance_name}的IP{ip_addr}异常")
            ip_addr = change_ip(client, domain, instance_name, ip_addr)
        else:
            logger.info(f"服务器{instance_name}的IP{ip_addr}正常")
            continue

        updated_ips[domain] = ip_addr
        
    # checked_ip_list = [ip["ipAddress"] for ip in client.get_static_ips()["staticIps"]]
    return updated_ips

def check_lightsail(aws_key, aws_secret, regions, force):
    updated_ips = {}
    for region_name in regions.split(","):
        logger.info(f"检查区域{region_name}")
        client = boto3.client(
            "lightsail",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=region_name,
        )
        updated_ips.update(check_region(client, force))
        
    return updated_ips
