import json


def get_subnet():
    with open('simple_ipam.json') as f:
        data = json.load(f)
        for key, value in data.items():
            print(key, value)
            if value == "free":
                data[key] = "busy"
                with open('simple_ipam.json', 'w') as file:
                    json.dump(data, file, indent=2)
                return key
