"use client";

import { useMemo, useState } from "react";
import dagre from "dagre";
import { useTelemetryStore, type TelemetryEvent } from "@/stores/telemetryStore";
import AgentNode, { type AgentNodeData } from "./AgentNode";
import NodeDetailPanel from "./NodeDetailPanel";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;

const stateColors: Record<string, string> = {
  IDLE: "#6B6558",
  THINKING: "#CC785C",
  SPAWNING: "#8A9AA8",
  EXECUTING: "#8BA888",
  DONE: "#90C8A8",
  ERROR: "#B87870",
};

function buildGraph(events: TelemetryEvent[]) {
  const nodeMap = new Map<string, AgentNodeData>();
  const edges: [string, string][] = [];
  const edgeSet = new Set<string>();
  let activeSubAgent: string | null = null;

  for (const evt of events) {
    const { node_id, node_type, state, narrative, metadata } = evt;

    // Skip token events and invalid events
    if (!node_id || (evt as any).type === "token") continue;

    if (!nodeMap.has(node_id)) {
      nodeMap.set(node_id, {
        id: node_id,
        label: node_id.replace(/_/g, " "),
        nodeType: node_type as AgentNodeData["nodeType"],
        state,
        narrative,
        metadata,
        x: 0,
        y: 0,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
      });
    } else {
      const existing = nodeMap.get(node_id)!;
      existing.state = state;
      if (narrative) existing.narrative = narrative;
      if (metadata) existing.metadata = metadata;
    }

    if (node_type === "SubAgent" && state === "EXECUTING") {
      activeSubAgent = node_id;
    }

    if (node_type === "SubAgent") {
      const edgeKey = `manager->${node_id}`;
      if (!edgeSet.has(edgeKey)) {
        edgeSet.add(edgeKey);
        edges.push(["manager", node_id]);
      }
    }

    if (node_type === "Module" && activeSubAgent) {
      const edgeKey = `${activeSubAgent}->${node_id}`;
      if (!edgeSet.has(edgeKey)) {
        edgeSet.add(edgeKey);
        edges.push([activeSubAgent, node_id]);
      }
    }
  }

  return { nodes: nodeMap, edges };
}

function layoutGraph(nodes: Map<string, AgentNodeData>, edges: [string, string][]): AgentNodeData[] {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", ranksep: 100, nodesep: 60 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const [id, node] of nodes) {
    g.setNode(id, { width: node.width, height: node.height });
  }

  for (const [from, to] of edges) {
    if (nodes.has(from) && nodes.has(to)) {
      g.setEdge(from, to);
    }
  }

  dagre.layout(g);

  const result: AgentNodeData[] = [];
  for (const [id, node] of nodes) {
    const pos = g.node(id);
    result.push({
      ...node,
      x: pos.x - node.width / 2,
      y: pos.y - node.height / 2,
    });
  }

  return result;
}

export default function DAGCanvas() {
  const events = useTelemetryStore((s) => s.events);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { layoutedNodes, edges, selectedNode } = useMemo(() => {
    if (events.length === 0) return { layoutedNodes: [], edges: [], selectedNode: null };

    const { nodes, edges: rawEdges } = buildGraph(events);
    const layouted = layoutGraph(nodes, rawEdges);
    const selected = selectedNodeId ? nodes.get(selectedNodeId) || null : null;

    return { layoutedNodes: layouted, edges: rawEdges, selectedNode: selected };
  }, [events, selectedNodeId]);

  if (layoutedNodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--pemali-text-muted)] text-sm">
        Waiting for agent activity...
      </div>
    );
  }

  const maxX = Math.max(...layoutedNodes.map((n) => n.x + n.width)) + 40;
  const maxY = Math.max(...layoutedNodes.map((n) => n.y + n.height)) + 40;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div
        className="flex-1 overflow-auto relative"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      >
        <div style={{ position: "relative", width: maxX, height: maxY, minWidth: "100%", minHeight: "100%" }}>
          <svg
            style={{ position: "absolute", top: 0, left: 0, width: maxX, height: maxY, pointerEvents: "none" }}
          >
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="var(--pemali-text-muted)" />
              </marker>
            </defs>
            {edges.map(([from, to], i) => {
              const fromNode = layoutedNodes.find((n) => n.id === from);
              const toNode = layoutedNodes.find((n) => n.id === to);
              if (!fromNode || !toNode) return null;

              const x1 = fromNode.x + fromNode.width / 2;
              const y1 = fromNode.y + fromNode.height;
              const x2 = toNode.x + toNode.width / 2;
              const y2 = toNode.y;

              const edgeColor = stateColors[fromNode.state] || stateColors.IDLE;

              return (
                <line
                  key={`${from}-${to}-${i}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={edgeColor}
                  strokeWidth={1.5}
                  strokeOpacity={0.4}
                  markerEnd="url(#arrowhead)"
                />
              );
            })}
          </svg>

          {layoutedNodes.map((node) => (
            <AgentNode
              key={node.id}
              node={node}
              isSelected={selectedNodeId === node.id}
              onClick={() => setSelectedNodeId(selectedNodeId === node.id ? null : node.id)}
            />
          ))}
        </div>
      </div>

      {selectedNode && (
        <NodeDetailPanel node={selectedNode} onClose={() => setSelectedNodeId(null)} />
      )}
    </div>
  );
}
