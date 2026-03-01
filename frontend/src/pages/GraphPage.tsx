import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { motion, AnimatePresence } from 'framer-motion';
import { useApi } from '../api/client';
import { useAuth } from '../context/AuthContext';
import EmptyState from '../components/EmptyState';
import * as THREE from 'three';
import {
  GlobeAltIcon,
  XMarkIcon,
  HashtagIcon,
  ArrowsPointingOutIcon,
  CubeIcon,
  EyeIcon,
  AdjustmentsHorizontalIcon,
  SparklesIcon,
  ArrowPathIcon,
  ViewfinderCircleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  created_at: string | null;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

interface Item {
  id: string;
  text: string;
  metadata: any;
}

interface SelectedNode {
  id: string;
  name: string;
  text: string;
  connections: number;
  group: number;
  type?: string;
  created_at?: string | null;
}

// Color palette for node groups (by type) — agentic types highlighted
const TYPE_COLORS: Record<string, string> = {
  agent: '#8b5cf6',      // violet — AI agents
  session: '#f97316',    // orange — agent sessions
  task: '#3b82f6',       // blue — agent tasks
  person: '#a78bfa',
  project: '#60a5fa',
  technology: '#10b981',
  organization: '#f59e0b',
  event: '#ef4444',
  concept: '#ec4899',
  location: '#06b6d4',
  document: '#84cc16',
  default: '#111111',
};

const GROUP_COLORS = [
  '#111111', '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316',
];

const GraphPage: React.FC = () => {
  const { token } = useAuth();
  const api = useApi();
  const [items, setItems] = useState<Item[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [useRealGraph, setUseRealGraph] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const [particlesEnabled, setParticlesEnabled] = useState(true);
  const [labelsVisible, setLabelsVisible] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [searchFilter, setSearchFilter] = useState('');
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [hoverNode, setHoverNode] = useState<any>(null);
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Responsive sizing
  useEffect(() => {
    const updateDims = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateDims();
    window.addEventListener('resize', updateDims);
    return () => window.removeEventListener('resize', updateDims);
  }, []);

  // Fetch data — try real graph endpoint first, fall back to list
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const resp = await api.get('/api/memory/graph', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (resp.data.nodes && resp.data.nodes.length > 0) {
          setGraphNodes(resp.data.nodes);
          setGraphEdges(resp.data.edges || []);
          setUseRealGraph(true);
          return;
        }
      } catch {
        // Graph endpoint not available or empty — fall back to list
      }
      try {
        const resp = await api.get('/api/memory/list', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setItems(resp.data.items || []);
        setUseRealGraph(false);
      } catch (e: any) {
        setError(e.message);
      }
    })();
  }, [token]);

  // Build graph data — real graph API or fallback clustering
  const graphData = useMemo(() => {
    // Real graph data from /api/memory/graph
    if (useRealGraph && graphNodes.length > 0) {
      const typeList = [...new Set(graphNodes.map((n) => n.type?.toLowerCase() || 'default'))];
      const nodes = graphNodes.map((n) => {
        const t = n.type?.toLowerCase() || 'default';
        return {
          id: n.id,
          name: n.label || n.id,
          text: n.label || n.id,
          val: 3 + Math.random() * 3,
          group: typeList.indexOf(t),
          type: t,
          created_at: n.created_at,
        };
      });
      const nodeIds = new Set(nodes.map((n) => n.id));
      const links = graphEdges
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .map((e) => ({
          source: e.source,
          target: e.target,
          value: 1,
          label: e.label,
        }));
      return { nodes, links };
    }

    // Fallback: build from memory list
    if (items.length === 0) return { nodes: [], links: [] };

    const keywords = ['auth', 'api', 'user', 'data', 'config', 'test', 'deploy', 'build', 'error', 'log'];
    const getGroup = (text: string) => {
      const lower = text.toLowerCase();
      for (let i = 0; i < keywords.length; i++) {
        if (lower.includes(keywords[i])) return i;
      }
      return 0;
    };

    const nodes = items.map((i) => ({
      id: i.id,
      name: i.text.slice(0, 40),
      text: i.text,
      val: 2 + Math.random() * 4,
      group: getGroup(i.text),
    }));

    const links: { source: string; target: string; value: number }[] = [];
    for (let idx = 0; idx < items.length - 1; idx++) {
      links.push({ source: items[idx].id, target: items[idx + 1].id, value: 1 });
    }
    const groupMap: Record<number, string[]> = {};
    nodes.forEach((n) => {
      if (!groupMap[n.group]) groupMap[n.group] = [];
      groupMap[n.group].push(n.id);
    });
    Object.values(groupMap).forEach((ids) => {
      for (let i = 0; i < ids.length - 1; i++) {
        if (Math.random() > 0.5) {
          const j = Math.min(i + 2, ids.length - 1);
          if (i !== j && !links.find((l) => l.source === ids[i] && l.target === ids[j])) {
            links.push({ source: ids[i], target: ids[j], value: 0.5 });
          }
        }
      }
    });

    return { nodes, links };
  }, [items, graphNodes, graphEdges, useRealGraph]);

  // Filter data
  const filteredData = useMemo(() => {
    if (!searchFilter.trim()) return graphData;
    const q = searchFilter.toLowerCase();
    const matchIds = new Set(
      graphData.nodes.filter((n) => n.text.toLowerCase().includes(q)).map((n) => n.id)
    );
    return {
      nodes: graphData.nodes.filter((n) => matchIds.has(n.id)),
      links: graphData.links.filter((l) => matchIds.has(l.source as string) && matchIds.has(l.target as string)),
    };
  }, [graphData, searchFilter]);

  // Stats
  const stats = useMemo(() => {
    const groups = new Set(graphData.nodes.map((n) => n.group));
    return {
      nodes: graphData.nodes.length,
      edges: graphData.links.length,
      clusters: groups.size,
    };
  }, [graphData]);

  // Highlight on hover
  const handleNodeHover = useCallback(
    (node: any) => {
      const newHighlightNodes = new Set<string>();
      const newHighlightLinks = new Set<string>();

      if (node) {
        newHighlightNodes.add(node.id);
        graphData.links.forEach((link: any) => {
          const srcId = typeof link.source === 'object' ? link.source.id : link.source;
          const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
          if (srcId === node.id || tgtId === node.id) {
            newHighlightNodes.add(srcId);
            newHighlightNodes.add(tgtId);
            newHighlightLinks.add(`${srcId}_${tgtId}`);
          }
        });
      }

      setHighlightNodes(newHighlightNodes);
      setHighlightLinks(newHighlightLinks);
      setHoverNode(node || null);
    },
    [graphData]
  );

  const handleNodeClick = useCallback(
    (node: any) => {
      setSelected({
        id: node.id,
        name: node.name,
        text: node.text,
        connections: graphData.links.filter(
          (l: any) =>
            (typeof l.source === 'string' ? l.source : l.source.id) === node.id ||
            (typeof l.target === 'string' ? l.target : l.target.id) === node.id
        ).length,
        group: node.group,
        type: node.type,
        created_at: node.created_at,
      });
      // Focus camera on node
      if (graphRef.current) {
        const distance = 120;
        const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
        graphRef.current.cameraPosition(
          { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
          node,
          1200
        );
      }
    },
    [graphData]
  );

  // Custom 3D node objects
  const nodeThreeObject = useCallback(
    (node: any) => {
      const isHighlighted = highlightNodes.has(node.id);
      const isSelectedNode = selected?.id === node.id;
      const baseRadius = 3 + (node.val || 1) * 0.8;
      const color = node.type
        ? TYPE_COLORS[node.type] || TYPE_COLORS.default
        : GROUP_COLORS[node.group % GROUP_COLORS.length];

      const group = new THREE.Group();

      // Core sphere
      const geometry = new THREE.SphereGeometry(baseRadius, 24, 24);
      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: isHighlighted || !hoverNode ? 0.9 : 0.2,
        shininess: 80,
        emissive: new THREE.Color(color),
        emissiveIntensity: isSelectedNode ? 0.4 : isHighlighted ? 0.2 : 0.05,
      });
      const sphere = new THREE.Mesh(geometry, material);
      group.add(sphere);

      // Outer glow ring for selected/hovered
      if (isSelectedNode) {
        const ringGeo = new THREE.RingGeometry(baseRadius + 2, baseRadius + 3, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(color),
          transparent: true,
          opacity: 0.3,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        group.add(ring);
      }

      // Label sprite
      if (labelsVisible && (isHighlighted || isSelectedNode)) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        canvas.width = 256;
        canvas.height = 64;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Background pill
        const text = node.name || '';
        ctx.font = 'bold 22px Inter, system-ui, sans-serif';
        const textWidth = ctx.measureText(text).width;
        const pillWidth = textWidth + 24;
        const pillX = (canvas.width - pillWidth) / 2;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.beginPath();
        ctx.roundRect(pillX, 8, pillWidth, 36, 18);
        ctx.fill();

        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, 26);

        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        const spriteMat = new THREE.SpriteMaterial({
          map: texture,
          transparent: true,
          depthTest: false,
        });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(28, 7, 1);
        sprite.position.set(0, baseRadius + 8, 0);
        group.add(sprite);
      }

      return group;
    },
    [highlightNodes, hoverNode, selected, labelsVisible]
  );

  // Auto-rotate
  useEffect(() => {
    if (graphRef.current) {
      const controls = graphRef.current.controls();
      if (controls) {
        controls.autoRotate = autoRotate;
        controls.autoRotateSpeed = 0.5;
      }
    }
  }, [autoRotate]);

  // Initial camera positioning
  useEffect(() => {
    if (graphRef.current && (items.length > 0 || graphNodes.length > 0)) {
      setTimeout(() => {
        graphRef.current?.zoomToFit(800, 80);
      }, 1500);
    }
  }, [items, graphNodes]);

  const resetView = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(600, 60);
      setSelected(null);
    }
  };

  if (!token) {
    return (
      <EmptyState
        icon={GlobeAltIcon}
        title="Agent Graph Explorer"
        description="Authenticate first to visualize your agent memory graph."
        action={{ label: 'Go to Playground', onClick: () => (window.location.href = '/demo') }}
      />
    );
  }

  if (items.length === 0 && graphNodes.length === 0 && !error) {
    return (
      <EmptyState
        icon={GlobeAltIcon}
        title="No agent memories yet"
        description="Attach an AI agent and store some observations, then come back to see the knowledge graph."
        action={{ label: 'Attach Agent', onClick: () => (window.location.href = '/demo') }}
      />
    );
  }

  return (
    <div className="relative -mx-8 -mt-6 -mb-28" style={{ height: 'calc(100vh - 52px)' }}>
      {/* Error banner */}
      {error && (
        <div className="absolute top-4 left-4 z-20 px-4 py-2.5 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-600 shadow-lg">
          {error}
        </div>
      )}

      {/* ── Top Bar Overlay ── */}
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        {/* Left: Title + Stats */}
        <div className="flex items-center gap-3 pointer-events-auto">
          <div className="flex items-center gap-3 px-4 py-2.5 bg-white/80 backdrop-blur-xl border border-black/[0.06] rounded-2xl shadow-[0_2px_16px_rgba(0,0,0,0.06)]">
            <CubeIcon className="w-5 h-5 text-gray-900" />
            <div>
              <h2 className="text-[14px] font-bold text-gray-900 leading-none">Agent Memory Graph</h2>
              <p className="text-[11px] text-gray-400 mt-0.5">Agents · Sessions · Tasks</p>
            </div>
          </div>

          {/* Stats pills */}
          <div className="flex items-center gap-1.5">
            {[
              { label: 'Nodes', value: stats.nodes, color: 'bg-black text-white' },
              { label: 'Edges', value: stats.edges, color: 'bg-white/80 text-gray-700 border border-black/[0.06]' },
              { label: 'Clusters', value: stats.clusters, color: 'bg-white/80 text-gray-700 border border-black/[0.06]' },
            ].map((s) => (
              <span
                key={s.label}
                className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold backdrop-blur-xl shadow-sm ${s.color}`}
              >
                {s.value} {s.label}
              </span>
            ))}
          </div>
        </div>

        {/* Right: Search + Controls */}
        <div className="flex items-center gap-2 pointer-events-auto">
          {/* Search */}
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              placeholder="Filter nodes..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-44 pl-8 pr-3 py-2 text-[12px] bg-white/80 backdrop-blur-xl border border-black/[0.06] rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black/10 shadow-sm"
            />
          </div>

          {/* Control buttons */}
          <div className="flex items-center gap-1 px-1.5 py-1 bg-white/80 backdrop-blur-xl border border-black/[0.06] rounded-2xl shadow-sm">
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`p-2 rounded-xl transition-all duration-200 ${autoRotate ? 'bg-black text-white' : 'text-gray-400 hover:text-gray-700 hover:bg-black/[0.04]'}`}
              title="Auto-rotate"
            >
              <ArrowPathIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setLabelsVisible(!labelsVisible)}
              className={`p-2 rounded-xl transition-all duration-200 ${labelsVisible ? 'bg-black text-white' : 'text-gray-400 hover:text-gray-700 hover:bg-black/[0.04]'}`}
              title="Toggle labels"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setParticlesEnabled(!particlesEnabled)}
              className={`p-2 rounded-xl transition-all duration-200 ${particlesEnabled ? 'bg-black text-white' : 'text-gray-400 hover:text-gray-700 hover:bg-black/[0.04]'}`}
              title="Toggle particles"
            >
              <SparklesIcon className="w-4 h-4" />
            </button>
            <div className="w-px h-5 bg-black/[0.06] mx-0.5" />
            <button
              onClick={resetView}
              className="p-2 rounded-xl text-gray-400 hover:text-gray-700 hover:bg-black/[0.04] transition-all duration-200"
              title="Reset view"
            >
              <ViewfinderCircleIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ── 3D Graph Canvas ── */}
      <div ref={containerRef} className="w-full h-full bg-gradient-to-b from-gray-50 to-white">
        <ForceGraph3D
          ref={graphRef}
          graphData={filteredData}
          width={dimensions.width}
          height={dimensions.height}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          linkColor={(link: any) => {
            const srcId = typeof link.source === 'object' ? link.source.id : link.source;
            const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
            const key = `${srcId}_${tgtId}`;
            if (highlightLinks.has(key)) return 'rgba(0,0,0,0.4)';
            return hoverNode ? 'rgba(0,0,0,0.03)' : 'rgba(0,0,0,0.08)';
          }}
          linkWidth={(link: any) => {
            const srcId = typeof link.source === 'object' ? link.source.id : link.source;
            const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
            const key = `${srcId}_${tgtId}`;
            return highlightLinks.has(key) ? 2 : 0.5;
          }}
          linkOpacity={0.6}
          linkDirectionalParticles={particlesEnabled ? 2 : 0}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.004}
          linkDirectionalParticleColor={() => '#000'}
          backgroundColor="#00000000"
          showNavInfo={false}
          enableNodeDrag={true}
          cooldownTicks={200}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      </div>

      {/* ── Hover tooltip ── */}
      <AnimatePresence>
        {hoverNode && !selected && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="fixed bottom-32 left-1/2 -translate-x-1/2 z-20 px-4 py-2.5 bg-black text-white rounded-2xl shadow-xl text-[12px] font-medium max-w-xs truncate pointer-events-none"
          >
            {hoverNode.text?.slice(0, 80) || hoverNode.name}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Legend ── */}
      <div className="absolute bottom-6 left-4 z-10 flex items-center gap-2 px-3 py-2 bg-white/80 backdrop-blur-xl border border-black/[0.06] rounded-2xl shadow-sm">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mr-1">
          {useRealGraph ? 'Types' : 'Groups'}
        </span>
        {useRealGraph
          ? [...new Set(graphNodes.map((n) => n.type?.toLowerCase() || 'default'))].slice(0, 8).map((t) => (
              <div key={t} className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TYPE_COLORS[t] || TYPE_COLORS.default }} />
                <span className="text-[9px] text-gray-500 capitalize">{t}</span>
              </div>
            ))
          : GROUP_COLORS.slice(0, Math.min(stats.clusters, 6)).map((color, i) => (
              <div key={i} className="flex items-center gap-1">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              </div>
            ))
        }
      </div>

      {/* ── Node Detail Panel ── */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, x: 320, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 320, scale: 0.95 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="absolute top-20 right-4 w-[320px] z-20 bg-white/90 backdrop-blur-2xl border border-black/[0.06] rounded-2xl shadow-[0_8px_40px_rgba(0,0,0,0.08)] overflow-hidden"
          >
            {/* Header with color bar */}
            <div
              className="h-1.5 w-full"
              style={{ backgroundColor: GROUP_COLORS[selected.group % GROUP_COLORS.length] }}
            />

            <div className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: GROUP_COLORS[selected.group % GROUP_COLORS.length] }}
                  />
                  <h3 className="text-[14px] font-bold text-gray-900">Node Details</h3>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="p-1.5 rounded-xl hover:bg-black/[0.04] transition-colors"
                >
                  <XMarkIcon className="w-4 h-4 text-gray-400" />
                </button>
              </div>

              {/* ID */}
              <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-black/[0.02] rounded-xl">
                <HashtagIcon className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-[11px] font-mono text-gray-500 truncate">{selected.id}</span>
              </div>

              {/* Content */}
              <div className="mb-4">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Content</p>
                <p className="text-[13px] text-gray-700 leading-relaxed bg-black/[0.015] rounded-xl p-3">
                  {selected.text}
                </p>
              </div>

              {/* Meta row */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-black text-white rounded-lg text-[11px] font-semibold">
                  {selected.connections} connections
                </span>
                {selected.type ? (
                  <span
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-white"
                    style={{ backgroundColor: TYPE_COLORS[selected.type] || TYPE_COLORS.default }}
                  >
                    {selected.type}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-black/[0.04] rounded-lg text-[11px] font-semibold text-gray-500">
                    Group {selected.group}
                  </span>
                )}
                {selected.created_at && (
                  <span className="text-[10px] text-gray-400">
                    {new Date(selected.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>

              {/* Available in AI tools */}
              <div className="mt-4 pt-4 border-t border-black/[0.06]">
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Available in AI tools</p>
                <div className="flex flex-wrap gap-1.5">
                  {['Claude', 'Cursor', 'LangGraph', 'CrewAI'].map((tool) => (
                    <span key={tool} className="px-2 py-0.5 text-[10px] font-medium text-gray-600 bg-black/[0.03] border border-black/[0.06] rounded-lg">
                      {tool}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `tg.recall(query="${selected.text?.slice(0, 40) || selected.name}", cross_session=True)`
                    );
                  }}
                  className="mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold text-gray-500 bg-black/[0.03] border border-black/[0.06] rounded-xl hover:bg-black/[0.06] transition-colors"
                >
                  Copy context for agent
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Keyboard hint ── */}
      <div className="absolute bottom-6 right-4 z-10 flex items-center gap-3 px-3 py-2 bg-white/80 backdrop-blur-xl border border-black/[0.06] rounded-2xl shadow-sm">
        <span className="text-[10px] text-gray-400">
          <kbd className="px-1.5 py-0.5 bg-black/[0.04] rounded text-[10px] font-mono">Scroll</kbd> Zoom
        </span>
        <span className="text-[10px] text-gray-400">
          <kbd className="px-1.5 py-0.5 bg-black/[0.04] rounded text-[10px] font-mono">Drag</kbd> Rotate
        </span>
        <span className="text-[10px] text-gray-400">
          <kbd className="px-1.5 py-0.5 bg-black/[0.04] rounded text-[10px] font-mono">Click</kbd> Select
        </span>
      </div>
    </div>
  );
};

export default GraphPage;