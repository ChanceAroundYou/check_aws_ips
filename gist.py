import gistyc
import requests
import json

class Gist(gistyc.GISTyc):
    def update_gist_content(self, gist_id, file_name, content):
        # Set the REST API url to update a GIST
        _query_url = f"https://api.github.com/gists/{gist_id}"

        # Read and parse the file
        rest_api_data = {
            'public': True,
            'files': {
                file_name: {
                    'content': content
                }
            }
        }

        # Update the GIST and get the response
        resp = requests.patch(_query_url, headers=self._headers, data=json.dumps(rest_api_data))
        resp_data = resp.json()

        return resp_data