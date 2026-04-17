'use client'

import { useState, useCallback } from 'react';
import ReactFlow, { Background, Controls, MiniMap, applyNodeChanges, applyEdgeChanges, NodeChange, EdgeChange, Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import SpanDrawer from './SpanDrawer';

interface TraceGraphProps {
  nodes: Node[];
  edges: Edge[];
}

export default function TraceGraph({ nodes: initialNodes, edges: initialEdges }: TraceGraphProps) {
  const [nodes, setNodes] = useState<Node[]>(initialNodes.map((n, i) => ({ ...n, position: { x: 250, y: i * 150 } })));
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [selectedSpan, setSelectedSpan] = useState<any | null>(null);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const onNodeClick = (_: any, node: Node) => {
    setSelectedSpan(node);
  };

  if (!nodes || nodes.length === 0) {
      return <div className="p-12 text-center">Select a run from the list to view its trace</div>;
  }

  return (
    <div className="w-full h-full flex overflow-hidden">
      <div className="flex-1 h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          fitView
        >
          <Background color="#ccc" gap={16} />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
      {selectedSpan && (
        <SpanDrawer span={selectedSpan} onClose={() => setSelectedSpan(null)} />
      )}
    </div>
  );
}
