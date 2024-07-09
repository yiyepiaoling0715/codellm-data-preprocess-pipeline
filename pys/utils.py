import os
import sys
import pytz
from datetime import datetime

from asset.config.config import RequestError
from asset.config.config import Config as AssetConfig
from asset.datasets.dataset import Dataset


# 描述信息
# describe='zyy datasets'
# 数据集tag
tags=['tag1', 'tag2']

def gen_dataset_version():
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now().astimezone(tz).strftime('%y-%m-%d-%H%M')

def get_lpai_token():
    # return lpai_token_zyy
    lpai_token = os.environ.get(LPAI_TOKEN_KEY)
    if not lpai_token:
        sys.stderr.write("Please set lpai access token in LPAI_TOKEN "
                         "enviroment variable before running this script.\n")
        sys.exit(1)
    return lpai_token


def print_path(dirpath_iter):
    for path_iter in os.listdir(dirpath_iter):
        path_iter=os.path.join(dirpath_iter,path_iter)
        if os.path.isdir(path_iter):
            print_path(path_iter)
        else:
            print('文件路径=',path_iter)
