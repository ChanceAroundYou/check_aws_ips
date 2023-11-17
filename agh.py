import requests

class Adguardhome:
    def __init__(self, name, password, base_url):
        self.name = name
        self.password = password
        self.base_url = base_url
        self.cookies = self.get_cookies()

    def get_cookies(self):
        url = f"{self.base_url}/login"
        payload = {
            'name': self.name,
            'password': self.password
        }
        response = requests.post(url, json=payload)
        return response.cookies
    
    def get_rewrite_dict(self):
        url = f"{self.base_url}/rewrite/list"
        response = requests.get(url, cookies=self.cookies)
        rewrite_dict = { rewrite['domain']: rewrite['answer'] for rewrite in response.json()}
        return rewrite_dict
    
    def _add_rewrite(self, domain, ip):
        url = f"{self.base_url}/rewrite/add"
        payload = {
            'domain': domain,
            'answer': ip
        }
        requests.post(url, json=payload, cookies=self.cookies)
    
    def _update_rewrite(self, domain, ip, old_ip):
        url = f"{self.base_url}/rewrite/update"
        payload = {
            "target":{"answer":old_ip,"domain":domain},
            "update":{"answer":ip,"domain":domain}
        }
        requests.put(url, json=payload, cookies=self.cookies)
    
    def _delete_rewrite(self, domain, ip):
        url = f"{self.base_url}/rewrite/delete"
        payload = {
            'domain': domain,
            'answer': ip
        }
        requests.post(url, json=payload, cookies=self.cookies)
    
    def add_or_update_rewrite(self, domain, ip):
        rewrite_list = self.get_rewrite_dict()
        if domain in rewrite_list:
            old_ip = rewrite_list[domain]
            self._update_rewrite(domain, ip, old_ip)
        else:
            self._add_rewrite(domain, ip)
            
    def delete_rewrite(self, domain):
        rewrite_list = self.get_rewrite_dict()
        if domain in rewrite_list:
            ip = rewrite_list[domain]
            self._delete_rewrite(domain, ip)
            
    def find_domain(self, ip):
        rewrite_list = self.get_rewrite_dict()
        for domain, rewrite_ip in rewrite_list.items():
            if ip == rewrite_ip:
                return domain
        return None


if __name__ == '__main__':
    name = 'name'
    password = 'password'
    base_url = 'http://agh/control'
    agh = Adguardhome(name, password, base_url)
    agh.get_cookies()
    rewrite_list = agh.get_rewrite_dict()
    print(rewrite_list)