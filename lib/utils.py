from datetime import datetime


def print_log(txt):
    time = datetime.now().time()
    time = time.strftime("%H:%M:%S")
    print(f"[INFO, {time}] {txt}")
