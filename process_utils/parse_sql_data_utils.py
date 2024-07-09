import re
import sys
import os
sys.path.append('../')
from process_utils.constants import PROJECT_ROOT_DIRPATH
import pymysql

# pattern_null=re.compile('[ \t\n]+')
def is_subsequence(s, sub):
    """
    检查子串sub是否为s的一个子序列
    """
    iter_s = iter(s)
    return all(c in iter_s for c in sub)

def has_repeated_subsequence(s):
    """
    检查字符串s是否包含重复的非连续子字符串
    """
    n = len(s)
    # 检查所有可能的子字符串长度
    for length in range(5, n // 2 + 1):
        # 检查所有可能的子字符串
        for i in range(n - length + 1):
            sub = s[i:i+length]
            # 从剩余部分查找另一个子序列
            remaining = s[:i] + s[i+length:]
            if is_subsequence(remaining, sub):
                counter=s.count(sub)
                return True,sub,counter
    return False,None,None

def calc_lens(lens,name):
        lens_sort=sorted(lens,reverse=False)
        p01_len=lens_sort[int(len(lens_sort)*0.01)]
        p10_len=lens_sort[int(len(lens_sort)*0.1)]
        p20_len=lens_sort[int(len(lens_sort)*0.2)]
        p30_len=lens_sort[int(len(lens_sort)*0.3)]
        p40_len=lens_sort[int(len(lens_sort)*0.4)]
        p50_len=lens_sort[int(len(lens_sort)*0.5)]
        p80_len=lens_sort[int(len(lens_sort)*0.8)]
        p90_len=lens_sort[int(len(lens_sort)*0.9)]
        p95_len=lens_sort[int(len(lens_sort)*0.95)]
        p99_len=lens_sort[int(len(lens_sort)*0.99)]
        p100_len=lens_sort[-1]
        print(f'{name} 长度分布 p01_len={p01_len},p10_len={p10_len},p20_len={p20_len},p30_len={p30_len},p40_len={p40_len},p50_len={p50_len},p80_len={p80_len},p90_len={p90_len},p95_len={p95_len},p99_len={p99_len},p100_len={p100_len}')


def get_all_repo_names():
    lines_inall=[]
    file_dirpath=os.path.join(PROJECT_ROOT_DIRPATH,'files')
    csv_filenames=[file for file in os.listdir(file_dirpath) if file.endswith('csv')]
    for csv_filename in csv_filenames:
        csv_filepath=os.path.join(file_dirpath,csv_filename)
        with open(csv_filepath,'r',encoding='utf-8') as fr:
            lines=[line.replace('.git','').strip('\r\n ').split('/')[-1] for line in fr]
            lines=[line.replace('_','').replace('-','').lower() for line in lines if line]
            lines_inall.extend(lines)
    print(lines_inall)
    print(len(lines_inall),len(list(set(lines_inall))))
    return set(lines_inall)
    
sql_for_multi_task="""
        
    
    """


# 打开数据库连接
db = pymysql.connect(host='localhost', user='yourusername', password='yourpassword', database='yourdatabase')

# 使用 cursor() 方法创建一个游标对象 cursor
cursor = db.cursor(pymysql.cursors.DictCursor)


if __name__=='__main__':
    get_all_repo_name()


