import os

def main():
    dirpaths=[]
    for dirpath in dirpaths:
        os.walk(dirpath, topdown=True, onerror=None, followlinks=False)