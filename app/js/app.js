/* =============================================================================
 * app.js — Entrega 2 (controlador)
 *
 * Liga os dados (graph.json), os ALGORITMOS (algorithms.js, do zero) e o
 * RENDER (render.js, D3). Cuida da UI: modos, painel de métricas e controles.
 * ===========================================================================*/
(function (global) {
  "use strict";
  const A = global.Algorithms;
  const R = global.GraphRender;
  const $ = (id) => document.getElementById(id);

  // estado ----------------------------------------------------------------
  let fullGraph = null;   // grafo completo do dataset atual
  let viewGraph = null;   // subgrafo efetivamente desenhado (após filtro de peso)
  let adj = null;         // lista de adjacência do viewGraph
  let mode = "bfs";       // 'bfs' | 'dfs' | 'components' | 'path'
  let selected = null;    // id do nó selecionado
  let pathPick = [];      // ids escolhidos no modo caminho
  let stopAnim = null;    // cancela animação em curso

  const HELP = {
    bfs: "BFS — clique num ingrediente: os vizinhos acendem por NÍVEL (distância em arestas). O número em cada nó é a distância até o selecionado.",
    dfs: "DFS — clique num ingrediente e aperte ▶ Rodar DFS. A numeração mostra a ORDEM de visita em profundidade. Compare com a ordem por nível (BFS) ao lado.",
    components: "Componentes — cada cor é um componente conexo. Ingredientes isolados (componente de tamanho 1) ficam destacados com anel tracejado.",
    path: "Caminho mínimo — clique no ingrediente de ORIGEM e depois no de DESTINO. O app traça e anima o menor caminho (em arestas) via BFS.",
  };

  // ---- carregamento dos dados (fetch; fallback p/ bundle em file://) --------
  async function loadGraph(which) {
    const url = which === "mock" ? "data/graph.mock.json" : "data/graph.json";
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (r.ok) return await r.json();
    } catch (e) { /* file:// bloqueia fetch -> usa bundle abaixo */ }
    const bundled = which === "mock" ? global.GRAPH_MOCK : global.GRAPH_REAL;
    if (bundled) return bundled;
    throw new Error("Não consegui carregar " + url + ". Rode via servidor local (ex.: Live Server / 'python -m http.server').");
  }

  // ---- monta o subgrafo visível aplicando o filtro de peso mínimo -----------
  function buildView() {
    const minW = +$("weight").value;
    const edges = fullGraph.edges.filter((e) => (e.weight || 1) >= minW);
    const keep = new Set();
    for (const e of edges) { keep.add(e.source); keep.add(e.target); }
    // grafos pequenos: mantém todos os nós (inclusive isolados, p/ a demo);
    // grafos grandes: só os que sobraram com aresta (legibilidade na banca).
    const small = fullGraph.nodes.length <= 60;
    const nodes = fullGraph.nodes.filter((n) => small || keep.has(n.id) || n.id === selected);
    viewGraph = { nodes, edges, meta: fullGraph.meta, stats: fullGraph.stats };
    adj = A.buildAdjacency(viewGraph);
    R.setGraph(viewGraph);
    updateMetrics();
    applyMode(true);
  }

  // ---- métricas -------------------------------------------------------------
  function updateMetrics() {
    const cc = A.connectedComponents(adj);
    let largest = 0; cc.sizes.forEach((s) => { if (s > largest) largest = s; });
    $("m-vertices").textContent = viewGraph.nodes.length;
    $("m-edges").textContent = viewGraph.edges.length;
    $("m-components").textContent = cc.count;
    $("m-largest").textContent = largest;

    // validação: meu algoritmo no grafo COMPLETO x campo do contrato
    const fadj = A.buildAdjacency(fullGraph);
    const fcc = A.connectedComponents(fadj);
    const expected = fullGraph.stats ? fullGraph.stats.num_components : fcc.count;
    const ok = fcc.count === expected;
    $("validation").innerHTML = "Validação dos componentes (meu algoritmo no dataset completo): <b>" +
      fcc.count + "</b> — contrato diz <b>" + expected + "</b> " + (ok ? "✅ confere" : "⚠️ difere");

    // top-N por grau (no grafo visível)
    const top = viewGraph.nodes
      .map((n) => ({ n, d: A.degree(adj, n.id) }))
      .sort((a, b) => b.d - a.d).slice(0, 10);
    $("topn").innerHTML = top.map((t, i) =>
      `<li data-id="${t.n.id}"><span class="rk">${i + 1}</span> ${t.n.emoji || "🥄"} ${t.n.name} <span class="dg">${t.d}</span></li>`
    ).join("");
    $("topn").querySelectorAll("li").forEach((li) =>
      li.addEventListener("click", () => onNodeClick(li.dataset.id)));

    // meta do dataset
    const m = fullGraph.meta || {};
    $("dataset-meta").textContent =
      `${m.source || "?"} · ${fullGraph.nodes.length} ingredientes, ${fullGraph.edges.length} arestas (dataset completo)`;
  }

  function setSelected(id) {
    selected = id;
    const n = id ? viewGraph.nodes.find((x) => x.id === id) : null;
    $("m-selected-name").textContent = n ? (n.emoji + " " + n.name) : "—";
    $("m-degree").textContent = id ? A.degree(adj, id) : "—";
  }

  // ---- modos ----------------------------------------------------------------
  // troca o modo ativo: ajusta a UI, limpa destaques e dispara o algoritmo do modo.
  function applyMode(silent) {
    if (stopAnim) { stopAnim(); stopAnim = null; }
    $("mode-help").textContent = HELP[mode];
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
    $("dfs-controls").style.display = mode === "dfs" ? "" : "none";
    $("path-controls").style.display = mode === "path" ? "" : "none";
    $("orders").style.display = mode === "dfs" ? "" : "none";
    pathPick = [];
    R.resetStyles();
    if (mode === "components") runComponents();
    else if (selected && mode === "bfs") runBFS(selected);
    if (mode === "path") $("path-info").textContent = "Clique na ORIGEM…";
    if (!silent) R.reheat();
  }

  // clique num ingrediente: a ação depende do MODO ativo (bfs/dfs/componentes/caminho).
  function onNodeClick(id) {
    setSelected(id);
    if (mode === "bfs") runBFS(id);
    else if (mode === "dfs") { R.markSelected(id); $("orders").querySelectorAll(".ord-list").forEach((e) => e.innerHTML = ""); }
    else if (mode === "path") pathStep(id);
    else if (mode === "components") R.markSelected(id);
  }

  // BFS: calcula os níveis a partir do nó (algorithms.bfsLevels) e pinta o grafo por nível.
  function runBFS(id) {
    const level = A.bfsLevels(adj, id);
    R.colorByLevel(level, id);
    let maxd = 0; level.forEach((v) => { if (v > maxd) maxd = v; });
    $("path-info").textContent = "";
    $("bfs-info").textContent = `Alcançáveis a partir de ${viewGraph.nodes.find((n) => n.id === id).emoji} ${id}: ${level.size} · distância máxima: ${maxd}`;
  }

  // DFS: ordem de visita em profundidade a partir do nó selecionado; mostra também a
  // ordem por nível (BFS) do mesmo nó, lado a lado, para evidenciar a diferença.
  function runDFS() {
    if (!selected) { flash("Selecione um ingrediente primeiro."); return; }
    const order = A.dfsOrder(adj, selected);
    const level = A.bfsLevels(adj, selected);
    // ordem BFS = vértices ordenados por nível (estável)
    const bfsOrder = [...level.entries()].sort((a, b) => a[1] - b[1]).map((e) => e[0]);
    renderOrder("dfs-order", order, "DFS (profundidade)");
    renderOrder("bfs-order", bfsOrder, "BFS (por nível)");
    if (stopAnim) stopAnim();
    stopAnim = R.animateDFS(order, 300);
  }

  function renderOrder(elId, order, _title) {
    $(elId).innerHTML = order.slice(0, 40).map((id, i) => {
      const n = viewGraph.nodes.find((x) => x.id === id);
      return `<span class="ord">${i + 1}.${n ? n.emoji : ""}</span>`;
    }).join(" ");
  }

  // Componentes conexas: rotula cada vértice e pinta cada componente de uma cor;
  // conta quantos são isolados (tamanho 1).
  function runComponents() {
    const cc = A.connectedComponents(adj);
    R.colorComponents(cc.component, cc.sizes);
    let isolated = 0; cc.sizes.forEach((s) => { if (s === 1) isolated++; });
    $("bfs-info").textContent = `${cc.count} componentes · ${isolated} ingrediente(s) isolado(s)`;
  }

  // modo caminho: junta dois cliques (1º = origem, 2º = destino) e então traça a rota.
  function pathStep(id) {
    pathPick.push(id);
    if (pathPick.length === 1) { $("path-info").textContent = "Origem: " + label(id) + " — agora clique no DESTINO…"; R.markSelected(id); }
    else if (pathPick.length === 2) { tracePath(pathPick[0], pathPick[1]); pathPick = []; }
  }

  // caminho mínimo em arestas (BFS + reconstrução, em algorithms.shortestPath),
  // com animação da rota; avisa quando não há caminho (componentes diferentes).
  function tracePath(a, b) {
    const path = A.shortestPath(adj, a, b);
    if (!path) { $("path-info").textContent = `Sem caminho entre ${label(a)} e ${label(b)} (componentes diferentes).`; R.resetStyles(); return; }
    $("path-info").textContent = `${label(a)} → ${label(b)}: ${path.length - 1} aresta(s) · ${path.map((id) => emojiOf(id)).join(" → ")}`;
    if (stopAnim) stopAnim();
    stopAnim = R.animatePath(path, 340);
  }

  const nodeOf = (id) => viewGraph.nodes.find((n) => n.id === id);
  const emojiOf = (id) => { const n = nodeOf(id); return n ? n.emoji : "🥄"; };
  const label = (id) => { const n = nodeOf(id); return n ? n.emoji + " " + n.name : id; };
  function flash(msg) { const s = $("status"); s.textContent = msg; s.classList.add("show"); clearTimeout(flash._t); flash._t = setTimeout(() => s.classList.remove("show"), 2400); }

  // ---- boot -----------------------------------------------------------------
  async function switchDataset(which) {
    try {
      fullGraph = await loadGraph(which);
    } catch (e) { flash(e.message); return; }
    selected = null; setSelected(null);
    const wmax = Math.max(1, ...fullGraph.edges.map((e) => e.weight || 1));
    const small = fullGraph.nodes.length <= 60;
    const def = small ? 1 : Math.max(1, Math.round(wmax * 0.18)); // grafo grande: começa filtrado
    $("weight").max = wmax; $("weight").value = def; $("weight-val").textContent = def;
    $("weight-row").style.display = small ? "none" : "";
    buildView();
  }

  function init() {
    R.init($("graph"), { onNodeClick });
    document.querySelectorAll(".mode-btn").forEach((b) =>
      b.addEventListener("click", () => { mode = b.dataset.mode; applyMode(); }));
    $("dataset").addEventListener("change", (e) => switchDataset(e.target.value));
    $("weight").addEventListener("input", (e) => { $("weight-val").textContent = e.target.value; buildView(); });
    $("run-dfs").addEventListener("click", runDFS);
    $("reset").addEventListener("click", () => { selected = null; setSelected(null); R.resetStyles(); R.fitView(0); applyMode(); });
    $("preset-path").addEventListener("click", () => {
      const a = nodeOf("egg") ? "egg" : viewGraph.nodes[0].id;
      const cands = ["saffron", "honey", "cinnamon", "vanilla"].filter((x) => nodeOf(x));
      const b = cands[0] || viewGraph.nodes[viewGraph.nodes.length - 1].id;
      mode = "path"; applyMode(); tracePath(a, b);
    });
    $("graph").addEventListener("click", () => { /* clique no fundo não faz nada */ });
    switchDataset("real");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})(window);
