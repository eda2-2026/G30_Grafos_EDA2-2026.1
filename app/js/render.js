/* =============================================================================
 * render.js — Entrega 2
 *
 * Camada de DESENHO/LAYOUT do grafo. Usa o D3 APENAS para:
 *   - layout force-directed (d3-force: posiciona os nós);
 *   - zoom/pan (d3-zoom);
 *   - desenho em SVG e transições.
 * NENHUM algoritmo de grafo aqui — BFS/DFS/componentes/caminho vivem em
 * algorithms.js. O D3 é lib de RENDER/LAYOUT (permitida pelo enunciado).
 *
 * Layout: força com CENTRO + COLISÃO (sem sobreposição) e SEM clamp retangular
 * → o grafo forma um "miolo" orgânico centrado, em vez de empilhar nos cantos.
 *
 * Expõe window.GraphRender.
 * ===========================================================================*/
(function (global) {
  "use strict";
  const d3 = global.d3;

  // cores por NÍVEL de BFS (distância): 0 = origem, 1, 2, 3, 4+
  const LEVEL_COLORS = ["#e8553e", "#16a07a", "#3d7fd6", "#9b6dd6", "#c98a1a"];
  // paleta para COMPONENTES (ciclo)
  const COMP_COLORS = [
    "#e8553e", "#16a07a", "#3d7fd6", "#9b6dd6", "#c98a1a",
    "#d4537e", "#5a8f3c", "#b5651d", "#7a5cc0", "#2aa6b8",
  ];
  const PATH_COLOR = "#f0b429";

  let svg, gRoot, gLinks, gNodes, zoom, sim;
  let nodes = [], links = [], byId = new Map();
  let nodeSel, linkSel;
  let radius = () => 12;
  let showLabels = true;
  let W = 800, H = 600;
  let onNodeClick = null;

  function init(svgEl, options) {
    options = options || {};
    onNodeClick = options.onNodeClick || null;
    svg = d3.select(svgEl);
    zoom = d3.zoom().scaleExtent([0.15, 5]).on("zoom", (ev) => gRoot.attr("transform", ev.transform));
    svg.call(zoom).on("dblclick.zoom", null);
    gRoot = svg.append("g");
    gLinks = gRoot.append("g").attr("class", "links");
    gNodes = gRoot.append("g").attr("class", "nodes");
    measure();
    global.addEventListener("resize", () => { measure(); if (sim) sim.force("center", d3.forceCenter(W / 2, H / 2)).alpha(0.2).restart(); });
  }

  function measure() {
    const r = svg.node().getBoundingClientRect();
    W = Math.max(320, r.width); H = Math.max(320, r.height);
  }

  // ---- carrega um grafo {nodes, edges} e (re)inicia o layout -----------------
  function setGraph(graph) {
    if (sim) sim.stop();
    measure();
    nodes = graph.nodes.map((n) => ({ ...n }));
    byId = new Map(nodes.map((n) => [n.id, n]));
    links = graph.edges
      .filter((e) => byId.has(e.source) && byId.has(e.target) && e.source !== e.target)
      .map((e) => ({ source: e.source, target: e.target, weight: e.weight || 1 }));

    // grau (a partir das arestas renderizadas) -> raio
    const deg = new Map(nodes.map((n) => [n.id, 0]));
    for (const l of links) { deg.set(l.source, deg.get(l.source) + 1); deg.set(l.target, deg.get(l.target) + 1); }
    const dmax = Math.max(1, ...deg.values());
    radius = (id) => 9 + 15 * Math.sqrt((deg.get(id) || 0) / dmax);
    showLabels = nodes.length <= 60; // grafos grandes: rótulo só no destaque

    const wmax = Math.max(1, ...links.map((l) => l.weight));

    // ---- arestas
    linkSel = gLinks.selectAll("line").data(links, (d) => d.source + "~" + d.target);
    linkSel.exit().remove();
    linkSel = linkSel.enter().append("line")
      .attr("class", "link")
      .attr("stroke-width", (d) => 0.7 + 2.3 * (d.weight / wmax))
      .merge(linkSel);

    // ---- nós
    nodeSel = gNodes.selectAll("g.node").data(nodes, (d) => d.id);
    nodeSel.exit().remove();
    const ne = nodeSel.enter().append("g").attr("class", "node")
      .on("click", (ev, d) => { ev.stopPropagation(); if (onNodeClick) onNodeClick(d.id); })
      .call(d3.drag()
        .on("start", (ev, d) => { if (!ev.active) sim.alphaTarget(0.25).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag", (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on("end", (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    ne.append("circle").attr("class", "dot");
    ne.append("text").attr("class", "emoji").attr("text-anchor", "middle").attr("dominant-baseline", "central").text((d) => d.emoji || "🥄");
    ne.append("text").attr("class", "label").attr("text-anchor", "middle").text((d) => d.name || d.id);
    ne.append("text").attr("class", "badge").attr("text-anchor", "middle"); // nº (nível/ordem)
    nodeSel = ne.merge(nodeSel);

    nodeSel.select("circle.dot").attr("r", (d) => radius(d.id))
      .style("fill", "var(--node-bg)").style("stroke", "var(--node-stroke)").style("stroke-width", 1.4);
    nodeSel.select("text.emoji").attr("font-size", (d) => Math.max(12, radius(d.id) * 1.05));
    nodeSel.select("text.label").attr("y", (d) => radius(d.id) + 13).style("display", showLabels ? null : "none");

    // ---- simulação (CENTRO + COLISÃO, sem clamp retangular)
    sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => 38 + 30 * (1 - d.weight / wmax)).strength(0.25))
      .force("charge", d3.forceManyBody().strength(nodes.length > 120 ? -90 : -240))
      .force("center", d3.forceCenter(W / 2, H / 2))
      .force("collide", d3.forceCollide((d) => radius(d.id) + 5).iterations(2))
      .force("x", d3.forceX(W / 2).strength(0.04))
      .force("y", d3.forceY(H / 2).strength(0.04))
      .on("tick", ticked);

    // PRÉ-AQUECE o layout de forma SÍNCRONA (não depende de requestAnimationFrame,
    // que fica pausado em abas ocultas). O grafo já nasce assentado e centrado;
    // o rAF continua só para o arrasto (drag) quando a página está visível.
    sim.stop();
    const warm = Math.min(400, 80 + nodes.length);
    for (let i = 0; i < warm; i++) sim.tick();
    ticked();
    resetStyles();
    fitView(0);
  }

  function ticked() {
    linkSel.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
    nodeSel.attr("transform", (d) => `translate(${d.x},${d.y})`);
  }

  // enquadra o grafo na viewport (após a simulação assentar um pouco)
  function fitView(delay) {
    setTimeout(() => {
      if (!nodes.length) return;
      const xs = nodes.map((n) => n.x), ys = nodes.map((n) => n.y);
      const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
      const gw = Math.max(1, maxX - minX), gh = Math.max(1, maxY - minY);
      const scale = Math.min(2, 0.86 * Math.min(W / gw, H / gh));
      const tx = W / 2 - scale * (minX + maxX) / 2, ty = H / 2 - scale * (minY + maxY) / 2;
      const t = d3.zoomIdentity.translate(tx, ty).scale(scale);
      if (delay) svg.transition().duration(500).call(zoom.transform, t);
      else svg.call(zoom.transform, t);          // instantâneo (não depende de rAF)
    }, delay || 0);
  }

  // ---------------------------------------------------------- destaques ------
  function resetStyles() {
    if (!nodeSel) return;
    nodeSel.classed("faded", false).classed("isolated", false).classed("sel", false);
    nodeSel.select("circle.dot").style("fill", "var(--node-bg)").style("stroke", "var(--node-stroke)").style("stroke-width", 1.4);
    nodeSel.select("text.badge").text("").style("display", "none");
    nodeSel.select("text.label").style("display", showLabels ? null : "none");
    if (linkSel) linkSel.classed("active", false).classed("path", false).style("stroke", null).style("opacity", null);
  }

  function markSelected(id) {
    nodeSel.classed("sel", (d) => d.id === id);
    nodeSel.filter((d) => d.id === id).select("circle.dot")
      .style("stroke", "var(--sel)").style("stroke-width", 3.5);
  }

  /** BFS: pinta cada nó pela cor do seu NÍVEL; mostra a distância no nó. */
  function colorByLevel(level, source) {
    resetStyles();
    nodeSel.each(function (d) {
      const g = d3.select(this);
      if (level.has(d.id)) {
        const lv = level.get(d.id);
        g.classed("faded", false);
        g.select("circle.dot").style("fill", LEVEL_COLORS[Math.min(lv, LEVEL_COLORS.length - 1)])
          .style("stroke", "var(--node-stroke)").style("stroke-width", 1.4);
        g.select("text.badge").style("display", null).text(lv);
        g.select("text.label").style("display", null);
      } else {
        g.classed("faded", true);
        g.select("circle.dot").style("fill", "var(--node-bg)");
        g.select("text.badge").style("display", "none");
      }
    });
    markSelected(source);
    // arestas que ligam níveis consecutivos ficam ativas
    linkSel.classed("active", (d) =>
      level.has(d.source.id) && level.has(d.target.id) &&
      Math.abs(level.get(d.source.id) - level.get(d.target.id)) === 1);
  }

  /** DFS: anima a ORDEM de visita, numerando cada nó na sequência. */
  function animateDFS(order, stepMs, onDone) {
    resetStyles();
    nodeSel.classed("faded", true);
    let i = 0;
    const timer = setInterval(() => {
      if (i >= order.length) { clearInterval(timer); if (onDone) onDone(); return; }
      const id = order[i];
      nodeSel.filter((d) => d.id === id).classed("faded", false).each(function () {
        const g = d3.select(this);
        g.select("circle.dot").style("fill", "#3d7fd6");
        g.select("text.badge").style("display", null).text(i + 1);
        g.select("text.label").style("display", null);
      });
      i++;
    }, stepMs || 320);
    return () => clearInterval(timer);
  }

  /** Componentes: pinta cada componente de uma cor; marca os isolados. */
  function colorComponents(component, sizes) {
    resetStyles();
    nodeSel.each(function (d) {
      const c = component.get(d.id);
      const g = d3.select(this);
      g.select("circle.dot").style("fill", COMP_COLORS[c % COMP_COLORS.length]);
      if (sizes.get(c) === 1) { g.classed("isolated", true); g.select("text.label").style("display", null); }
    });
    linkSel.classed("active", true);
  }

  /** Caminho mínimo: realça a rota e anima nó a nó. */
  function animatePath(path, stepMs, onDone) {
    resetStyles();
    nodeSel.classed("faded", true);
    const inPath = new Set(path);
    linkSel.style("opacity", 0.08);
    let i = 0;
    const timer = setInterval(() => {
      if (i >= path.length) {
        clearInterval(timer);
        // acende as arestas da rota
        linkSel.filter((d) => inPath.has(d.source.id) && inPath.has(d.target.id) &&
          Math.abs(path.indexOf(d.source.id) - path.indexOf(d.target.id)) === 1)
          .classed("path", true).style("opacity", 1);
        if (onDone) onDone();
        return;
      }
      const id = path[i];
      nodeSel.filter((d) => d.id === id).classed("faded", false).each(function () {
        const g = d3.select(this);
        g.select("circle.dot").style("fill", PATH_COLOR).style("stroke", "#7a5200").style("stroke-width", 2.5);
        g.select("text.badge").style("display", null).text(i);
        g.select("text.label").style("display", null);
      });
      i++;
    }, stepMs || 360);
    return () => clearInterval(timer);
  }

  // reorganiza o force depois de um destaque (sem recriar o grafo)
  function reheat() { if (sim) sim.alpha(0.2).restart(); }

  global.GraphRender = {
    init, setGraph, resetStyles, markSelected, colorByLevel,
    animateDFS, colorComponents, animatePath, fitView, reheat,
    LEVEL_COLORS, COMP_COLORS, PATH_COLOR,
  };
})(window);
