import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DeleteDomainRecordRequest import DeleteDomainRecordRequest


class AliyunDNS:
    def __init__(self, keyid, secret, root_domain):
        self.client = AcsClient(ak=keyid, secret=secret)
        self.root_domain = root_domain

    def get_domain_record(self, sub_domain):
        request = DescribeDomainRecordsRequest()
        request.set_DomainName(self.root_domain)
        response = self.client.do_action_with_exception(request)
        records = json.loads(response)['DomainRecords']['Record']
        sub_record = filter(lambda record: record['RR'] == sub_domain, records)
        return list(sub_record)

    def add_domain_record(self, sub_domain, value, record_type='A'):
        request = AddDomainRecordRequest()
        request.set_DomainName(self.root_domain)
        request.set_RR(sub_domain)
        request.set_Type(record_type)
        request.set_Value(value)

        if record_type == 'A':
            request.set_TTL(600)
            request.set_Line('default')
        return self.client.do_action_with_exception(request)

    def update_domain_record(self, sub_domain, rid, value, record_type='A'):
        request = UpdateDomainRecordRequest()
        request.set_RR(sub_domain)
        request.set_Type(record_type)
        request.set_Value(value)
        request.set_RecordId(rid)

        if record_type == 'A':
            request.set_TTL(600)
            request.set_Line('default')
        return self.client.do_action_with_exception(request)
    
    def add_or_update_domain_record(self, sub_domain, value, record_type='A'):
        records = self.get_domain_record(sub_domain)
        if records:
            rid = records[0]['RecordId']
            old_value = records[0]['Value']
            if old_value != value:
                return self.update_domain_record(sub_domain, rid, value, record_type)
        else:
            return self.add_domain_record(sub_domain, value, record_type)

    def del_domain_record(self, sub_domain):
        records = self.get_domain_record(sub_domain)
        if records:
            rid = records[0]['RecordId']
            request = DeleteDomainRecordRequest()
            request.set_RecordId(rid)
            return self.client.do_action_with_exception(request)
