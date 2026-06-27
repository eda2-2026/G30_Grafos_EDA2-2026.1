"""
Algoritmos de grafo — IMPLEMENTADOS DO ZERO.

Nenhuma biblioteca de grafos (NetworkX, igraph, ...) é usada. A única
importação é `collections.deque`, que é apenas uma fila (estrutura de dados
genérica da stdlib), NÃO um algoritmo de grafo pronto.

IMPORTANTE — peso x distância:
    O peso da aresta representa FORÇA de co-ocorrência (nº de receitas), e NÃO
    custo de travessia. Por isso BFS mede distância em ARESTAS (saltos), tratando
    o grafo como não-ponderado, exatamente como pede o enunciado.

Complexidade (lista de adjacência, V vértices e E arestas):
    BFS .................. O(V + E)
    DFS .................. O(V + E)
    caminho mínimo (BFS) . O(V + E)
    componentes conexas .. O(V + E)   (cada vértice/aresta visitado 1 vez no total)
Memória: O(V) para as marcações de visita/nível/pai.
"""

from collections import deque


def bfs_levels(graph, source):
    """
    BFS a partir de `source`.

    Retorna um dict { vértice -> nível }, onde nível é a distância em arestas
    (nº de saltos) de `source` até o vértice. Só inclui vértices ALCANÇÁVEIS.

    Invariante da BFS: a fila contém vértices em ordem não-decrescente de nível,
    logo o primeiro caminho encontrado até cada vértice é o mais curto em saltos.

    Complexidade: O(V + E).
        Cada vértice entra na fila no máximo uma vez (marcação em `level`),
        e cada aresta é examinada no máximo duas vezes (uma por extremidade).
    """
    level = {source: 0}          # vértice -> distância; também faz as vezes de "visitado"
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v in graph.neighbors(u):
            if v not in level:          # ainda não visitado
                level[v] = level[u] + 1
                queue.append(v)
    return level


def dfs_preorder(graph, source):
    """
    DFS iterativa (com pilha explícita, para não estourar a recursão em grafos
    grandes) a partir de `source`.

    Retorna a lista de vértices na ordem de PRÉ-VISITA (ordem de descoberta).

    Complexidade: O(V + E) — mesma análise da BFS, trocando a fila pela pilha.
    """
    visited = set()
    order = []
    stack = [source]
    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        # Empilha vizinhos; o `if not in visited` evita reprocessar.
        for v in graph.neighbors(u):
            if v not in visited:
                stack.append(v)
    return order


def shortest_path(graph, a, b):
    """
    Caminho mínimo (em nº de arestas) de `a` até `b` via BFS, COM RECONSTRUÇÃO.

    Retorna a lista de vértices [a, ..., b] do caminho, ou None se b for
    inalcançável a partir de a. Se a == b, retorna [a].

    Como funciona a reconstrução:
        Mantemos `parent[v]` = vértice de onde v foi descoberto. Ao alcançar b,
        subimos pelos pais (b -> parent[b] -> ... -> a) e invertemos.

    Complexidade: O(V + E) para a busca + O(comprimento do caminho) para
    reconstruir = O(V + E).
    """
    if a == b:
        return [a]
    if not graph.has_node(a) or not graph.has_node(b):
        return None

    parent = {a: None}           # a é a raiz; também marca "visitado"
    queue = deque([a])
    while queue:
        u = queue.popleft()
        for v in graph.neighbors(u):
            if v not in parent:
                parent[v] = u
                if v == b:
                    return _reconstruct(parent, b)
                queue.append(v)
    return None                  # b nunca foi alcançado


def _reconstruct(parent, target):
    """Sobe pela cadeia de pais e devolve o caminho da raiz até `target`."""
    path = [target]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def connected_components(graph):
    """
    Rotula cada vértice com o id do seu componente conexo, via flood-fill BFS.

    Retorna (component, num_components):
        component : dict { vértice -> id_componente }  (ids 0, 1, 2, ...)
        num_components : quantidade total de componentes

    Por que é O(V + E) no TOTAL (e não O(V * (V+E))):
        Percorremos todos os vértices uma vez; só iniciamos uma BFS a partir
        de um vértice ainda NÃO rotulado. Cada vértice é rotulado exatamente
        uma vez e cada aresta é examinada um nº constante de vezes ao longo de
        TODAS as buscas somadas. Logo o custo agregado é O(V + E).

    (Poderia usar DFS no lugar da BFS com a mesma complexidade — a escolha não
    altera o conjunto de componentes, apenas a ordem de visita.)
    """
    component = {}
    cid = 0
    for start in graph.nodes():
        if start in component:
            continue
        # Inunda o componente de `start` com o rótulo cid.
        component[start] = cid
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in graph.neighbors(u):
                if v not in component:
                    component[v] = cid
                    queue.append(v)
        cid += 1
    return component, cid


def farthest_node(graph, source):
    """
    A partir de `source`, devolve (vértice_mais_distante, distância) dentro do
    seu componente, usando uma BFS. Auxiliar para achar um par "distante".
    O(V + E).
    """
    level = bfs_levels(graph, source)
    far = max(level, key=level.get)
    return far, level[far]


def approx_diameter_path(graph, start):
    """
    Caminho longo (aproximação do diâmetro) dentro do componente de `start`,
    pela heurística clássica da DUPLA BFS:
        1) BFS de `start`        -> acha o vértice mais distante `a`
        2) BFS de `a`            -> acha o vértice mais distante `b`
        3) caminho mínimo a -> b
    Para árvores o resultado é exatamente o diâmetro; em grafos gerais é uma
    excelente aproximação e basta para exibir "dois ingredientes distantes".

    Retorna (a, b, caminho) — caminho é a lista de vértices. O(V + E).
    """
    a, _ = farthest_node(graph, start)
    b, _ = farthest_node(graph, a)
    return a, b, shortest_path(graph, a, b)
