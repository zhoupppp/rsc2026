import re
with open("sac_finish.html", "r") as f:
    text = f.read()
    match = re.search(r"function openPerson.*?\}", text, re.DOTALL)
    if match:
        print(match.group(0))
