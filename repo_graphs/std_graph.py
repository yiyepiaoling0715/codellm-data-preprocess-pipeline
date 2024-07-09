from typeing import Dict

from collections import defaultdict 
 
class Graph: 
    def __init__(self,vertices): 
        self.graph = defaultdict(list) 
        self.V = vertices
  
    def addEdge(self,u,v): 
        self.graph[u].append(v) 
  
    def topologicalSortUtil(self,v,visited,stack): 
  
        visited[v] = True
  
        for i in self.graph[v]: 
            if visited[i] == False: 
                self.topologicalSortUtil(i,visited,stack) 
  
        stack.insert(0,v) 
  
    def topologicalSort(self): 
        visited = [False]*self.V 
        stack =[] 
  
        for i in range(self.V): 
            if visited[i] == False: 
                self.topologicalSortUtil(i,visited,stack) 
  
        print (stack) 

print ("拓扑排序结果：")
# 5,    2,0
# 5,    2,3,0
# 5,    2,3,4,0,1

g= Graph(6) 
g.addEdge(5, 2); 
g.addEdge(5, 0); 
g.addEdge(4, 0); 
g.addEdge(4, 1); 
g.addEdge(2, 3); 
g.addEdge(3, 1); 
  
print ("拓扑排序结果：")
print(g.topologicalSort())

print('**************************')



class Graph(object):
    def __init__(self,vertices):
        self.graph = defaultdict(list)
        self.V = vertices
    def addEdge(self,u,v):
        self.graph[u].append(v)
    def topologicalSortUtil(self,v,visited,stack):
        visited[v]=True
        for i in self.graph[v]:
            if visited[i]==False:
                self.topologicalSortUtil(i,visited,stack)
        stack.insert(0,v)
    def topological_sort(self):
        visited=[False]*self.V 
        stack=[]
        for i in range(self.V):
            if visited[i]==False:
                self.topologicalSortUtil(i,visited,stack)

        print (stack) 


class PathGraph(object):
    def __init__(self,vertices):
        """
            vertices: 顶点数
        """
        self.graph = defaultdict(list)
        self.V=vertices
        self.node_2_index_dict={}
        self.index_2_node_dict={}

    def node_2_index(self,filepath_2_node_dict:Dict):
        index=0
        for filepath_iter, node_iter in filepath_2_node_dict.items():
            self.node_2_index_dict[node_iter]=index
            self.index_2_node_dict[index]=node_iter
            index+=1

    def add_edge(self,path_node_obj):
        for in_node_iter in path_node_obj.in_nodes:
            self.graph[path_node_obj].append(in_node_iter)
    
    def topological_sort_util(self,cur_node,visited,stack):
        visited[self.node_2_index[cur_node]]=True
        for in_node_iter in self.graph[cur_node]:
            if visited[self.node_2_index[in_node_iter]]==False:
                self.topological_sort_util(in_node_iter,visited,stack)
        stack.insert(0,cur_node)

    def topological_sort(self):
        visited=[False]*self.V
        stack=[]
        for i in range(self.V):
            if visited[i]==False:
                self.topological_sort_util(self.index_2_node_dict[i],visited,stack)
        print(stack)








print ("自我实现 拓扑排序结果：")
# 5,    2,0
# 5,    2,3,0
# 5,    2,3,4,0,1

g= Graph(6) 
g.addEdge(5, 2); 
g.addEdge(5, 0); 
g.addEdge(4, 0); 
g.addEdge(4, 1); 
g.addEdge(2, 3); 
g.addEdge(3, 1); 
  
print ("拓扑排序结果：")
print(g.topological_sort())

print('**************************')


from collections import defaultdict 

 ####发现上面的代码有点问题（不知道是不是我的问题），所以我自己写了一个，同时也加深下对于拓扑的了解
class Graph: 
    # 构造函数
    def __init__(self,vertices): 
        # 创建用处存储图中点之间关系的dict{v: [u, i]}(v,u,i都是点,表示边<v, u>, <v, i>)：边集合
        self.graph = defaultdict(list) 
        # 存储图中点的个数
        self.V = vertices

    # 添加边
    def addEdge(self,u,v): 
        # 添加边<u, v>
        self.graph[u].append(v) 
    # 获取一个存储图中所有点的状态:dict{key: Boolean}
    # 初始时全为False
    def set_keys_station(self):
        keyStation = {}
        key = list(self.graph.keys())
        # 因为有些点，没有出边，所以在key中找不到，需要对图遍历找出没有出边的点
        if len(key) < self.V:
            for i in key:
                for j in self.graph[i]:
                    if j not in key:
                        key.append(j)
        for ele in key:
            keyStation[ele] = False
        return keyStation

    # 拓扑排序
    def topological_sort(self):
        # 拓扑序列
        queue = []
        # 点状态字典
        station = self.set_keys_station()
        # 由于最坏情况下每一次循环都只能排序一个点，所以需要循环点的个数次
        for i in range(self.V):
            # 循环点状态字典，elem：点
            for elem in station:
                # 这里如果是已经排序好的点就不进行排序操作了
                if not station[elem]:
                    self.topological_sort_util(elem, queue, station)
        return queue   
    # 对于点进行排序     
    def topological_sort_util(self, elem, queue, station):
        # 设置点的状态为True，表示已经排序完成
        station[elem] = True
        # 循环查看该点是否有入边，如果存在入边，修改状态为False
        # 状态为True的点，相当于排序完成，其的边集合不需要扫描
        for i in station:
            if elem in self.graph[i] and not station[i]:
                station[elem] = False
        # 如果没有入边，排序成功，添加到拓扑序列中
        if station[elem]:
            queue.append(elem)


print ("拓扑排序结果：")
# 5,    2,0
# 5,    2,3,0
# 5,    2,3,4,0,1

g= Graph(6) 
g.addEdge(5, 2); 
g.addEdge(5, 0); 
g.addEdge(4, 0); 
g.addEdge(4, 1); 
g.addEdge(2, 3); 
g.addEdge(3, 1); 
  
print ("拓扑排序结果：")
print(g.topological_sort())


# class GraphA(object):
#     def __init__(self,vertices):
#         self.vertices=vertices
#         self.graph=defaultdict(list)
    
#     def addEdge(self,u,v):
#         self.graph[u]=v
    
#     def set_keys_station(self):
#         keyStation={}
#         keys=list(self.graph.keys())
#         if len(keys)<self.V:
#             for i in keys:
#                 for j in self.graph[i]:
#                     if j not in keys:
#                         keys.append(j)
#         for key in keys:
#             keyStation[key]=False
#         return keyStation
    
#     def topological_sort_util(self,elem,queue,station):



