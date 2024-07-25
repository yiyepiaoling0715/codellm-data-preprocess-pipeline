代码大模型领域,目前各大公司开源的都是模型,鲜少对数据处理过程有提及;但是数据处理是LLM应用中不可或缺的一环,因此我们决定开源我们的数据处理流程,以供大家参考.

处理流程图见 file/预训练数据处理架构.png

## 关键技术点:
    FIM,

    tree_sitter,

    文件拓扑图,

    函数依赖解析
## 有哪些优势
    50G的仓库,30min内处理完毕整个流程,二级多进程,多处多进程

    支持tres_sitter 代码语义解析,构建单行/多行/行内 FIM,长文件实现前后FIM拼接

    支持文件拓扑图,实现对 python/go/cpp/c的 头文件依赖解析,并构拓扑图,被依赖在前,依赖在后

    函数依赖解析,实现对python/go的函数依赖解析,函数构图,根据中心函数向外发散查找到1度函数，2度函数等，用于实现相关性搜索,RAG增强,测试用例训练数据整理

## 预训练代码数据清洗
```
    cd shells/
    bash multi_process_pipeline.sh
```
### 脚本中4大模块
#### python ../repo_graphs/multi_dedup_file.py 
    #src_dirpath_list  根目录列表，靠,切分，不同任务的原始的代码仓库在每个根目录下面，作为原始输入格式

    分仓库分语言分文件进行清洗,解析每个文件头文件,构建文件依赖关系

    对每个函数的依赖关系进行解析,构建函数级依赖关系

    整理为可去重文件形式

#### python -u ../clean/bigcode_dataset/near_deduplication/minhash_deduplication.py 

    文件级别清洗去重

    调用bigdata相关去重逻辑,minhash+graph
#### python -u $workdir/repo_graphs/multi_graph_repo.py 

    对去重后的文件进行构图,构建文件依赖关系图

    文件内容依据tree_sitter识别代码语义结构,构建fim语料

    正则清洗

    可逆数据替换

#### python -u $workdir/clean/bigcode_dataset/pii/main_process.py 

    基于bigdata处理逻辑，pii脱敏


## 微调数据清洗脚本
bash parse_sql_data.sh

## 解析仓库文件，生成测试用例训练数据
bash testcase_debug.sh

## 一些辅助工具
### 解压打包的仓库文件
bash assist/unzip_repo.sh

cd pys/assist
### 求最佳阈值,抑制幻觉
    python calc_logp_thres.py
### 随机选择评估数据集
    python create_data_reflow_eval.py
### 从sft训练数据格式,转为dpo数据格式
    python create_rl_data.py

cd testcase
### python gen_testcase.py
    生成测试用例训练数据