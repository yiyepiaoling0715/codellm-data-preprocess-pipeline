#!/usr/bin/env python
import pathlib
import sys
from datetime import datetime
from urllib.parse import urlparse

from isbinary import is_binary_file
import pandas as pd

dataset_base_name = 'rx_2_multigroup_priv_codebase'


def make_datafile_from_coderepo(repo_dir, datafile_dir,
                                # datafile_format='jsonl'
                                datafile_format='json'
                                ):
    # use pathliab to walk through the directory
    # and get the list of files
    repo_dir = pathlib.Path(repo_dir)
    datafile_dir = pathlib.Path(datafile_dir)
    datetime_str = datetime.now().strftime('%Y%m%d')
    #rx_2_multigroup_priv_codebase.20240318.hf
    dataset_name = dataset_base_name + '.' + datetime_str
    datafile_save_dir = datafile_dir / dataset_name / 'unique_json'
    merged_datafile_save_dir = datafile_dir / dataset_name / 'merged_json'
    merged_datafile_save_jsonpath = merged_datafile_save_dir/ 'merged.json'
    if not datafile_save_dir.exists():
        datafile_save_dir.mkdir(parents=True)
    if not merged_datafile_save_dir.exists():
        merged_datafile_save_dir.mkdir(parents=True)

    files = [f for f in repo_dir.glob('**/*') if f.is_file()
             and not f.name.startswith(str(repo_dir / '.git/')) and '.git' not in f.name]
    if not files:
        return False
    repo_dir = pathlib.Path(repo_dir)
    repo_revision = ''

    repo_metadata = {}
    repo_origin=get_repo_origin(repo_dir)
    repo_branch=get_repo_branch(repo_dir)
    repo_metadata['repo_origin'] = repo_origin  
    repo_metadata['repo_branch'] = repo_branch
    
    barch_path=repo_dir / '.git/refs/heads' / repo_metadata['repo_branch']
    print('barch_path=\t',barch_path)
    if not barch_path.exists():
        return False
    try:
        repo_revision=get_repo_revision(repo_dir, repo_metadata['repo_branch'])
    except Exception as e:
        print(e.args)
        repo_revision=f'{e.args}'
    repo_metadata['repo_revision'] = repo_revision
    repo_metadata['total_files'] = 0
    repo_metadata['total_size'] = 0
    repo_metadata['license'] = ['unknown']
    data_features = ['repo_origin', 'license', 'file_path', 'file_lines',
                     'file_size', 'file_extension', 'content']
    code_df = pd.DataFrame(columns=data_features)
    for index_file,f in enumerate(files):
        ##todo tmp 否则数据量的话太大
        # if index_file>5000:
        #     break
            
        # check if file is a link or not
        if f.is_symlink():
            continue
        # check if file is a binary file or not
        if is_binary_file(f):
            continue
        # get the file extension
        file_extension = f.suffix
        # get the file size
        file_size = f.stat().st_size
        # get the file content
        with open(f, 'r') as f_content:
            # get the file lines
            try:
                file_lines = sum(1 for line in f_content)
            except UnicodeDecodeError as e:
                print('报错内容',f_content)
                print('UnicodeDecodeError 报错文件',f)
                continue
                # raise ValueError('UnicodeDecodeError: %s' % e)
            f_content.seek(0)
            content = f_content.read()
        # update the repo metadata
        repo_metadata['total_size'] += file_size
        repo_metadata['total_files'] += 1
        # update the code dataframe
        f_row = {'repo_origin': repo_metadata['repo_origin'],
                'repo_name': repo_dir.name,
                 'license': repo_metadata['license'],
                 'file_path': str(f).replace(str(repo_dir) + '/', ''),
                 'file_lines': int(file_lines),
                 'file_size': int(file_size),
                 'file_extension': file_extension,
                 'content': content}
        code_df = code_df._append(f_row, ignore_index=True)
    code_df[['file_lines', 'file_size']] = code_df[
      ['file_lines', 'file_size']].astype(int)
    print('code_df describe=\n',
        code_df[['file_lines', 'file_size', 'file_extension']].describe(include='all'))

    # save the code dataframe
    # if datafile_format == 'jsonl':
    if datafile_format in ['jsonl','json']:
        # datafile_name = repo_dir.name + '.jsonl'
        # a_ep_data_datax-sync.json
        datafile_name = repo_dir.name + f'.{datafile_format}'
        cur_jsonl_path=datafile_save_dir / datafile_name
        code_df.to_json(cur_jsonl_path,orient='records', lines=True)
        print('保存jsonl路径=',cur_jsonl_path)
        code_df.to_json(merged_datafile_save_jsonpath,orient='records',lines=True,mode='a')
        print('merged_jsonpath=',merged_datafile_save_jsonpath)

    else:
        raise ValueError('还未实现')
    print('Repo origin: ', repo_metadata['repo_origin'])
    print('Repo branch: ', repo_metadata['repo_branch'])
    print('Repo revision: ', repo_metadata['repo_revision'])
    print('Total files: ', repo_metadata['total_files'])
    print('Total size: ', repo_metadata['total_size'])
    print('#' * 80)


def get_repo_origin(repo_dir):
    repo_dir = pathlib.Path(repo_dir)
    repo_origin = ''
    with open(repo_dir / '.git/config', 'r') as f:
        for line in f:
            if line.strip().startswith('url'):
                repo_origin = line.split('=')[1].strip()
                break
    if repo_origin:
        _parsed = urlparse(repo_origin)
        repo_origin = f"{_parsed.scheme}://{_parsed.netloc.split('@')[1]}"
        repo_origin += _parsed.path
    return repo_origin


def get_repo_branch(repo_dir):
    repo_dir = pathlib.Path(repo_dir)
    repo_branch = ''
    with open(repo_dir / '.git/HEAD', 'r') as f:
        for line in f:
            if line.startswith('ref'):
                repo_branch = line.split('/')[2].strip()
                break
    return repo_branch


def get_repo_revision(repo_dir, repo_branch='master'):
    print('repo_dir=',repo_dir)
    repo_dir = pathlib.Path(repo_dir)
    repo_revision = ''
    with open(repo_dir / '.git/refs/heads' / repo_branch, 'r') as f:
        repo_revision = f.read().strip()
        repo_revision = repo_revision[:7]
    return repo_revision


if __name__ == '__main__':
    repo_dir = sys.argv[1]
    datafile_dir = sys.argv[2]
    make_datafile_from_coderepo(repo_dir, datafile_dir,datafile_format='json')
