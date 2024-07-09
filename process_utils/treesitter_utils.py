from tree_sitter import Node,Tree
from typing import Generator,Text,List,Dict
import codecs
from process_utils.lang_processor import LangParserProxy,LangJudge
from process_utils.dedup_content import CommonPattern
from process_utils.constants import Constants
def traverse_tree(tree: Tree) -> Generator[Node, None, None]:
    cursor = tree.walk()
    visited_children = False
    while True:
        if not visited_children:
            yield cursor.node
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break

        # tree = parser.parse(source_bytes)
        # #for check begin
        # all_check_node_list=[node for node in traverse_tree(tree)]

def extract_imports_with_parser(filepath,parser):

    import_node_list:List[Node]=[]
    import_text_list:List[Text]=[]
    with open(filepath, "rb") as fw:
        source_bytes = fw.read()
    tree = parser.parse(source_bytes)
    all_check_node_list=[node for node in traverse_tree(tree)]
    # for node_iter in all_check_node_list[:100]:
    for node_iter in all_check_node_list[:5000]:
        try:
            node_text=codecs.decode(node_iter.text,'utf-8')
        except UnicodeDecodeError as e:
            print(f'e.args={e.args},UnicodeDecodeError,node_iter={node_iter}')
            continue
        # print(f'node_iter={node_iter}')
        # print(f'grammar_name={node_iter.grammar_name},text={node_iter.text}')
        if len(node_text)>3000:
            continue
        if len(node_iter.grammar_name)<3:
            continue
        # if pattern.search(node_text):
        # if node_iter.grammar_name not in import_grammar_name_list:
        if CommonPattern.general_import_pattern.search(node_text) and node_iter.grammar_name not in Constants.import_exclude_grammar_name_list:
            import_node_list.append(node_iter)
            import_text_list.append(node_text)
    return import_node_list
    # return {
    #     'import_node_list':import_node_list,
    #     'import_text_list':import_text_list   
    # }