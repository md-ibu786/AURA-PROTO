/**
 * ============================================================================
 * FILE: EntityGraph.tsx
 * LOCATION: frontend/src/features/kg-query/components/EntityGraph.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    SVG-based force-directed graph visualization for knowledge graph entities.
 *    Displays nodes colored by entity type with edges showing relationships.
 *    Supports node selection, hover highlighting, and zoom/pan controls.
 *
 * ROLE IN PROJECT:
 *    Graph visualization component for KG query feature. Shows entity
 *    relationships from the knowledge graph.
 *
 * @see: types/kg-query.types.ts - GraphData, GraphNode, GraphEdge types
 * @see: hooks/useKGQuery.ts - useGraphData hook
 * @see: pages/KGQueryPage.tsx - Parent component
 * @note: Uses simple force simulation without external dependencies
 */

import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';
import { GraphData, GraphNode, GraphEdge } from '../types/kg-query.types';

interface EntityGraphProps {
    data: GraphData;
    onNodeClick?: (node: GraphNode) => void;
    selectedNodeId?: string;
    width?: number;
    height?: number;
}

// Entity type colors
const ENTITY_COLORS: Record<string, string> = {
    Topic: '#4CAF50',
    Concept: '#2196F3',
    Methodology: '#FF9800',
    Finding: '#9C27B0',
    Chunk: '#607D8B',
    ParentChunk: '#795548',
    Document: '#E91E63',
    default: '#999999',
};

// Simple force simulation positions
function calculatePositions(
    nodes: GraphNode[],
    edges: GraphEdge[],
    width: number,
    height: number
): Map<string, { x: number; y: number }> {
    const positions = new Map<string, { x: number; y: number }>();

    // Initialize positions in a circle
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;

    nodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / nodes.length;
        positions.set(node.id, {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
        });
    });

    // Simple force simulation iterations
    const iterations = 50;
    const repulsion = 5000;
    const attraction = 0.05;

    for (let iter = 0; iter < iterations; iter++) {
        // Calculate repulsion between all nodes
        nodes.forEach((nodeA) => {
            const posA = positions.get(nodeA.id)!;
            let fx = 0;
            let fy = 0;

            nodes.forEach((nodeB) => {
                if (nodeA.id === nodeB.id) return;
                const posB = positions.get(nodeB.id)!;
                const dx = posA.x - posB.x;
                const dy = posA.y - posB.y;
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = repulsion / (dist * dist);
                fx += (dx / dist) * force;
                fy += (dy / dist) * force;
            });

            posA.x += fx * 0.1;
            posA.y += fy * 0.1;
        });

        // Calculate attraction along edges
        edges.forEach((edge) => {
            const posA = positions.get(edge.source);
            const posB = positions.get(edge.target);
            if (!posA || !posB) return;

            const dx = posB.x - posA.x;
            const dy = posB.y - posA.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = dist * attraction;

            posA.x += (dx / dist) * force;
            posA.y += (dy / dist) * force;
            posB.x -= (dx / dist) * force;
            posB.y -= (dy / dist) * force;
        });

        // Keep nodes within bounds
        nodes.forEach((node) => {
            const pos = positions.get(node.id)!;
            pos.x = Math.max(50, Math.min(width - 50, pos.x));
            pos.y = Math.max(50, Math.min(height - 50, pos.y));
        });
    }

    return positions;
}

export function EntityGraph({
    data,
    onNodeClick,
    selectedNodeId,
    width = 600,
    height = 400,
}: EntityGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const [zoom, setZoom] = useState(1);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    // Calculate node positions
    const positions = useMemo(
        () => calculatePositions(data.nodes, data.edges, width, height),
        [data.nodes, data.edges, width, height]
    );

    // Get connected nodes for highlighting
    const connectedNodes = useMemo(() => {
        const connected = new Set<string>();
        if (hoveredNodeId || selectedNodeId) {
            const targetId = hoveredNodeId || selectedNodeId;
            data.edges.forEach((edge) => {
                if (edge.source === targetId) connected.add(edge.target);
                if (edge.target === targetId) connected.add(edge.source);
            });
            connected.add(targetId!);
        }
        return connected;
    }, [hoveredNodeId, selectedNodeId, data.edges]);

    // Pan handlers
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        if (e.button === 0) {
            setIsDragging(true);
            setDragStart({ x: e.clientX, y: e.clientY });
        }
    }, []);

    const handleMouseMove = useCallback(
        (e: React.MouseEvent) => {
            if (isDragging) {
                setPan((prev) => ({
                    x: prev.x + (e.clientX - dragStart.x) / zoom,
                    y: prev.y + (e.clientY - dragStart.y) / zoom,
                }));
                setDragStart({ x: e.clientX, y: e.clientY });
            }
        },
        [isDragging, dragStart, zoom]
    );

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    // Zoom handlers
    const handleZoomIn = useCallback(() => {
        setZoom((prev) => Math.min(prev * 1.2, 3));
    }, []);

    const handleZoomOut = useCallback(() => {
        setZoom((prev) => Math.max(prev / 1.2, 0.3));
    }, []);

    const handleReset = useCallback(() => {
        setZoom(1);
        setPan({ x: 0, y: 0 });
    }, []);

    const handleFitView = useCallback(() => {
        // Calculate bounds
        let minX = Infinity,
            minY = Infinity,
            maxX = -Infinity,
            maxY = -Infinity;
        positions.forEach((pos) => {
            minX = Math.min(minX, pos.x);
            minY = Math.min(minY, pos.y);
            maxX = Math.max(maxX, pos.x);
            maxY = Math.max(maxY, pos.y);
        });

        const dataWidth = maxX - minX + 100;
        const dataHeight = maxY - minY + 100;
        const scaleX = width / dataWidth;
        const scaleY = height / dataHeight;
        const scale = Math.min(scaleX, scaleY, 1);

        setZoom(scale);
        setPan({
            x: (width / 2 - (minX + maxX) / 2) / scale,
            y: (height / 2 - (minY + maxY) / 2) / scale,
        });
    }, [positions, width, height]);

    // Auto-fit on data change
    useEffect(() => {
        if (data.nodes.length > 0) {
            handleFitView();
        }
    }, [data.nodes.length]); // eslint-disable-line react-hooks/exhaustive-deps

    if (data.nodes.length === 0) {
        return (
            <div className="entity-graph-empty">
                <p>No graph data available.</p>
                <p>Select a module to view its entity graph.</p>
                <style>{`
                    .entity-graph-empty {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: ${height}px;
                        color: var(--text-2);
                        text-align: center;
                    }
                `}</style>
            </div>
        );
    }

    return (
        <div className="entity-graph">
            {/* Controls */}
            <div className="graph-controls">
                <button onClick={handleZoomIn} title="Zoom in">
                    <ZoomIn size={16} />
                </button>
                <button onClick={handleZoomOut} title="Zoom out">
                    <ZoomOut size={16} />
                </button>
                <button onClick={handleFitView} title="Fit view">
                    <Maximize2 size={16} />
                </button>
                <button onClick={handleReset} title="Reset">
                    <RefreshCw size={16} />
                </button>
            </div>

            {/* Graph stats */}
            <div className="graph-stats">
                {data.nodeCount} nodes, {data.edgeCount} edges
            </div>

            {/* SVG Graph */}
            <svg
                ref={svgRef}
                width={width}
                height={height}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
            >
                <g transform={`scale(${zoom}) translate(${pan.x}, ${pan.y})`}>
                    {/* Edges */}
                    {data.edges.map((edge) => {
                        const sourcePos = positions.get(edge.source);
                        const targetPos = positions.get(edge.target);
                        if (!sourcePos || !targetPos) return null;

                        const isHighlighted =
                            connectedNodes.size === 0 ||
                            (connectedNodes.has(edge.source) && connectedNodes.has(edge.target));

                        return (
                            <g key={edge.id}>
                                <line
                                    x1={sourcePos.x}
                                    y1={sourcePos.y}
                                    x2={targetPos.x}
                                    y2={targetPos.y}
                                    stroke={isHighlighted ? '#666' : '#ddd'}
                                    strokeWidth={isHighlighted ? 1.5 : 1}
                                    strokeOpacity={isHighlighted ? 0.8 : 0.3}
                                />
                                {/* Edge label */}
                                <text
                                    x={(sourcePos.x + targetPos.x) / 2}
                                    y={(sourcePos.y + targetPos.y) / 2}
                                    fontSize={8}
                                    fill={isHighlighted ? '#666' : '#ccc'}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                >
                                    {edge.type}
                                </text>
                            </g>
                        );
                    })}

                    {/* Nodes */}
                    {data.nodes.map((node) => {
                        const pos = positions.get(node.id);
                        if (!pos) return null;

                        const color = ENTITY_COLORS[node.type] || ENTITY_COLORS.default;
                        const isSelected = node.id === selectedNodeId;
                        const isHovered = node.id === hoveredNodeId;
                        const isHighlighted = connectedNodes.size === 0 || connectedNodes.has(node.id);
                        const nodeRadius = isSelected || isHovered ? 12 : 10;

                        return (
                            <g
                                key={node.id}
                                transform={`translate(${pos.x}, ${pos.y})`}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onNodeClick?.(node);
                                }}
                                onMouseEnter={() => setHoveredNodeId(node.id)}
                                onMouseLeave={() => setHoveredNodeId(null)}
                                style={{ cursor: 'pointer' }}
                            >
                                {/* Node circle */}
                                <circle
                                    r={nodeRadius}
                                    fill={color}
                                    stroke={isSelected ? '#FFD400' : isHovered ? '#fff' : 'none'}
                                    strokeWidth={isSelected || isHovered ? 3 : 0}
                                    opacity={isHighlighted ? 1 : 0.3}
                                />
                                {/* Node label */}
                                <text
                                    y={nodeRadius + 12}
                                    fontSize={10}
                                    fill={isHighlighted ? '#333' : '#999'}
                                    textAnchor="middle"
                                    style={{ pointerEvents: 'none' }}
                                >
                                    {node.name.length > 15
                                        ? node.name.slice(0, 15) + '...'
                                        : node.name}
                                </text>
                            </g>
                        );
                    })}
                </g>
            </svg>

            {/* Legend */}
            <div className="graph-legend">
                {Object.entries(ENTITY_COLORS)
                    .filter(([key]) => key !== 'default')
                    .map(([type, color]) => (
                        <div key={type} className="legend-item">
                            <span
                                className="legend-dot"
                                style={{ backgroundColor: color }}
                            />
                            <span>{type}</span>
                        </div>
                    ))}
            </div>

            <style>{`
                .entity-graph {
                    position: relative;
                    background: var(--surface-1);
                    border: 1px solid var(--border-1);
                    border-radius: 8px;
                    overflow: hidden;
                }

                .graph-controls {
                    position: absolute;
                    top: 12px;
                    right: 12px;
                    display: flex;
                    gap: 4px;
                    z-index: 10;
                }

                .graph-controls button {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 32px;
                    height: 32px;
                    background: var(--surface-2);
                    border: 1px solid var(--border-1);
                    border-radius: 4px;
                    cursor: pointer;
                    color: var(--text-2);
                }

                .graph-controls button:hover {
                    background: var(--surface-3);
                    color: var(--text-1);
                }

                .graph-stats {
                    position: absolute;
                    top: 12px;
                    left: 12px;
                    font-size: 12px;
                    color: var(--text-3);
                    background: var(--surface-2);
                    padding: 4px 8px;
                    border-radius: 4px;
                }

                .graph-legend {
                    position: absolute;
                    bottom: 12px;
                    left: 12px;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    background: var(--surface-2);
                    padding: 8px 12px;
                    border-radius: 4px;
                    max-width: calc(100% - 24px);
                }

                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 11px;
                    color: var(--text-2);
                }

                .legend-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                }

                .entity-graph svg {
                    display: block;
                }
            `}</style>
        </div>
    );
}
