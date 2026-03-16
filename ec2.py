from calendar import c

import boto3
import retry
from botocore.client import BaseClient
from loguru import logger

from ping import detect_ip


def _get_domain_from_tags(tags, fallback):
    if not tags:
        return fallback

    for tag in tags:
        key = (tag.get("Key") or "").strip()
        value = (tag.get("Value") or "").strip()

        if key.lower() in {"domain", "dns", "fqdn"} and value:
            return value

        for candidate in (value, key):
            if "." in candidate:
                return candidate

    return fallback


def check_region(client: BaseClient, force=False):
    updated_ips = {}

    paginator = client.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                state = instance.get("State", {}).get("Name", "unknown")
                tags = instance.get("Tags", [])
                domain = _get_domain_from_tags(tags, instance_id)
                ip_addr = instance.get("PublicIpAddress")

                if state == "terminated":
                    logger.info(f"实例{instance_id}已终止, 跳过")
                    continue

                if not ip_addr:
                    logger.warning(f"实例{instance_id}没有公网IP, 跳过")
                    continue

                if force:
                    logger.warning(f"强制重启实例{instance_id}: {ip_addr}")
                    client.reboot_instances(InstanceIds=[instance_id])
                    changed = True
                elif not detect_ip(ip_addr, domain):
                    logger.error(f"实例{instance_id}的IP {ip_addr}异常, 重启实例")
                    client.reboot_instances(InstanceIds=[instance_id])
                    changed = True
                else:
                    logger.info(f"实例{instance_id}的IP {ip_addr}正常")
                    changed = False

                updated_ips[domain] = {
                    "ip": ip_addr,
                    "changed": changed,
                }

    return updated_ips


@retry.retry(tries=3, delay=5)
def check_ec2(aws_key, aws_secret, regions, force):
    updated_ips = {}
    for region_name in regions.split(","):
        region_name = region_name.strip()
        if not region_name:
            continue

        logger.info(f"检查区域{region_name}")
        client = boto3.client(
            "ec2",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=region_name,
        )
        updated_ips.update(check_region(client, force))

    return updated_ips
