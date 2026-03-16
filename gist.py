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
    
    def get_gist(self, gist_id, file_name=None):
        _query_url = f"https://api.github.com/gists/{gist_id}"
        resp = requests.get(_query_url, headers=self._headers)
        resp_data = resp.json()
        if file_name:
            return resp_data['files'][file_name]['content']
        return resp_data

if __name__ == '__main__':
    import configparser
    from datetime import datetime
    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')
    default = config['DEFAULT']
    gist_id = default['GIST_ID']
    token = default['GIST_TOKEN']
    domain = default['domain'] # Assuming domain is used as the filename in the gist

    # Initialize Gist with authentication token
    gist = Gist(token)

    # --- Test Reading Gist ---
    print(f"--- Reading Gist: {gist_id} ---")
    try:
        gist_data = gist.get_gist(gist_id, 'aws.xiaokubao.space')
        # Pretty print the JSON response
        print(json.dumps(gist_data, indent=4))
        print("--- Read successful ---")
    except Exception as e:
        print(f"Error reading gist: {e}")


    # --- Test Writing to Gist ---
    print(f"\n--- Updating Gist: {gist_id}, File: {domain} ---")
    try:
        # Prepare new content
        new_content = f"Last updated on: {datetime.now().isoformat()}"
        
        # Update the gist using the custom raw method
        update_response = gist.update_gist_content(
            gist_id=gist_id,
            file_name=domain,
            content=new_content
        )
        
        # Check if the update was successful by checking the response
        if 'id' in update_response:
            print("--- Update successful ---")
            # print(json.dumps(update_response, indent=4))
        else:
            print("--- Update failed ---")
            print(json.dumps(update_response, indent=4))

    except Exception as e:
        print(f"Error updating gist: {e}")
