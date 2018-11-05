# This is a helper for local testing using ngrok
import subprocess
import urllib.request
import re

def getUrl():
    # Return the current ngrok url
    with urllib.request.urlopen("http://localhost:4040/api/tunnels") as response:
        text = str(response.read())
    m = re.search(r"https://\w+\.ngrok\.io",text)
    url = m.group(0)

    return url


def start(command="ngrok http 8080"):
    # Start ngrok
    p = subprocess.Popen(command)


if __name__ == '__main__':
    start()
