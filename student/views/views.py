import json

def safe_log_data(data, action):
    json_string = json.dumps(data, indent=4)

    with open(f'/Users/diyorbekmajidov/Works/redesigned-quiz/logs/{action}_data.json', 'w') as file:
        file.write(json_string)