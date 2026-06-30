/* =============================================================================
 * algorithms.js — Entrega 2 (Rede de Ingredientes)
 *
 * BFS, DFS, COMPONENTES CONEXAS e CAMINHO MÍNIMO — IMPLEMENTADOS DO ZERO.
 * Nenhuma biblioteca de grafos é usada (o D3, em outro arquivo, só faz
 * layout/desenho — nunca algoritmo).
 *
 * Estrutura de dados: LISTA DE ADJACÊNCIA
 *     adj : Map< id_do_vertice , Array<id_vizinho> >
 *
 * O grafo é NÃO-DIRIGIDO e SEM LAÇOS. O peso das arestas existe nos dados
 * (co-ocorrência em receitas), mas BFS/DFS/caminho tratam o grafo como
 * NÃO-PONDERADO — a distância é medida em ARESTAS (saltos), como pede o tema.
 *
 * Complexidade (V vértices, E arestas):
 *     BFS .................. O(V + E)
 *     DFS .................. O(V + E)
 *     Componentes conexas .. O(V + E)  (total, cada vértice/aresta 1x)
 *     Caminho mínimo (BFS) . O(V + E)
 *     Memória .............. O(V)
 *
 * Expõe um único objeto global: window.Algorithms
 * ===========================================================================*/
(function (global) {
  "use strict";

  /**
   * Constrói a lista de adjacência a partir do contrato graph.json.
   * Ignora arestas com extremidade inexistente e laços (source === target).
   * O(V + E).
   */
  function buildAdjacency(graph) {
    const adj = new Map();
    for (const n of graph.nodes) {
      if (!adj.has(n.id)) adj.set(n.id, []);
    }
    for (const e of graph.edges) {
      if (e.source === e.target) continue;          // sem laços
      if (!adj.has(e.source) || !adj.has(e.target)) continue;
      adj.get(e.source).push(e.target);             // não-dirigido:
      adj.get(e.target).push(e.source);             // adiciona nos dois sentidos
    }
    return adj;
  }

  /**
   * BFS a partir de `source`.
   * Retorna Map< id -> nível >, onde nível é a distância em arestas até a
   * origem. Só inclui vértices ALCANÇÁVEIS.
   *
   * Invariante: a fila contém vértices em ordem não-decrescente de nível, logo
   * o primeiro caminho encontrado até cada vértice é o mais curto em saltos.
   * O(V + E): cada vértice entra na fila no máximo 1x; cada aresta é olhada 2x.
   */
  function bfsLevels(adj, source) {
    const level = new Map();
    level.set(source, 0);
    const queue = [source];
    let head = 0;                                   // fila por índice (O(1) amortizado)
    while (head < queue.length) {
      const u = queue[head++];
      for (const v of adj.get(u) || []) {
        if (!level.has(v)) {                         // ainda não visitado
          level.set(v, level.get(u) + 1);
          queue.push(v);
        }
      }
    }
    return level;
  }

  /**
   * DFS ITERATIVA (pilha explícita, para não estourar a recursão) a partir de
   * `source`. Retorna a lista de ids na ORDEM DE PRÉ-VISITA (descoberta).
   *
   * Os vizinhos são empilhados em ordem reversa para que a visita siga a ordem
   * natural da lista de adjacência (apenas estético; não altera a complexidade).
   * O(V + E).
   */
  function dfsOrder(adj, source) {
    const visited = new Set();
    const order = [];
    const stack = [source];
    while (stack.length) {
      const u = stack.pop();
      if (visited.has(u)) continue;                  // pode haver duplicata na pilha
      visited.add(u);
      order.push(u);
      const nbrs = adj.get(u) || [];
      for (let i = nbrs.length - 1; i >= 0; i--) {
        if (!visited.has(nbrs[i])) stack.push(nbrs[i]);
      }
    }
    return order;
  }

  /**
   * COMPONENTES CONEXAS via flood-fill (BFS por componente).
   * Retorna { component: Map<id->idComponente>, count: nº de componentes,
   *           sizes: Map<idComponente->tamanho> }.
   *
   * Custo O(V + E) NO TOTAL: cada vértice é rotulado uma única vez e cada
   * aresta examinada um nº constante de vezes somando-se TODAS as buscas.
   * (Poderia usar DFS no lugar da BFS, com a mesma complexidade.)
   */
  function connectedComponents(adj) {
    const component = new Map();
    const sizes = new Map();
    let cid = 0;
    for (const start of adj.keys()) {
      if (component.has(start)) continue;
      // inunda o componente de `start` com o rótulo cid
      component.set(start, cid);
      let size = 0;
      const queue = [start];
      let head = 0;
      while (head < queue.length) {
        const u = queue[head++];
        size++;
        for (const v of adj.get(u) || []) {
          if (!component.has(v)) {
            component.set(v, cid);
            queue.push(v);
          }
        }
      }
      sizes.set(cid, size);
      cid++;
    }
    return { component, count: cid, sizes };
  }

  /**
   * CAMINHO MÍNIMO (em nº de arestas) de `a` até `b` via BFS, COM
   * RECONSTRUÇÃO. Retorna a lista [a, ..., b] ou null se não houver caminho.
   * Se a === b, retorna [a].
   *
   * Mantemos parent[v] = de onde v foi descoberto; ao achar b, subimos pelos
   * pais e invertemos. O(V + E).
   */
  function shortestPath(adj, a, b) {
    if (a === b) return [a];
    if (!adj.has(a) || !adj.has(b)) return null;
    const parent = new Map();
    parent.set(a, null);
    const queue = [a];
    let head = 0;
    while (head < queue.length) {
      const u = queue[head++];
      for (const v of adj.get(u) || []) {
        if (!parent.has(v)) {
          parent.set(v, u);
          if (v === b) {                              // achou: reconstrói
            const path = [b];
            while (parent.get(path[path.length - 1]) != null) {
              path.push(parent.get(path[path.length - 1]));
            }
            return path.reverse();
          }
          queue.push(v);
        }
      }
    }
    return null;                                      // b inalcançável
  }

  /** Grau (nº de vizinhos distintos) de um vértice. */
  function degree(adj, id) {
    return new Set(adj.get(id) || []).size;
  }

  global.Algorithms = {
    buildAdjacency,
    bfsLevels,
    dfsOrder,
    connectedComponents,
    shortestPath,
    degree,
  };
})(window);
