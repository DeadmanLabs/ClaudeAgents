import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node {
  id: string;
  name: string;
  type: string;
  description?: string;
}

interface Link {
  source: string;
  target: string;
  label?: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

interface GraphViewProps {
  graphData: GraphData;
  isRunning: boolean;
}

export default function GraphView({ graphData, isRunning }: GraphViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Map node types to colors
  const nodeColors: Record<string, string> = {
    module: '#4338ca',   // indigo
    class: '#0369a1',    // blue
    function: '#0891b2', // cyan
    utility: '#047857',  // emerald
    component: '#65a30d', // lime
    service: '#ca8a04',   // yellow
    model: '#b91c1c',     // red
    interface: '#7e22ce', // purple
    // Fallback colors for other types
    database: '#9d174d',
    api: '#1e40af',
    ui: '#0f766e',
  };

  // Draw the graph using D3
  useEffect(() => {
    if (!svgRef.current) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Clear previous graph
    d3.select(svgRef.current).selectAll('*').remove();

    // If no data, show a message
    if (!graphData.nodes.length) {
      const svg = d3.select(svgRef.current)
        .attr('width', width)
        .attr('height', height);
        
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#666')
        .text('Component graph will appear here once planning starts');
        
      return;
    }

    // Create the SVG container
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', `translate(${width / 2}, ${height / 2})`);

    // Add a zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        svg.attr('transform', event.transform);
      });

    d3.select(svgRef.current).call(zoom);

    // Process links to use actual node objects
    const nodeMap = new Map<string, Node & d3.SimulationNodeDatum>();
    graphData.nodes.forEach(node => {
      nodeMap.set(node.id, { ...node, x: 0, y: 0 });
    });

    const links = graphData.links.map(link => ({
      source: nodeMap.get(link.source)!,
      target: nodeMap.get(link.target)!,
      label: link.label
    }));

    const nodes = Array.from(nodeMap.values());

    // Create the simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(0, 0))
      .on('tick', ticked);

    // Add the links
    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // Add link labels if they exist
    const linkLabels = svg.append('g')
      .selectAll('text')
      .data(links.filter(l => l.label))
      .enter()
      .append('text')
      .attr('font-size', '8px')
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .text(d => d.label || '');

    // Add the nodes
    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .call(d3.drag<SVGGElement, Node & d3.SimulationNodeDatum>()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    // Add tooltips for nodes
    const tooltip = d3.select('body')
      .append('div')
      .attr('class', 'absolute bg-black text-white p-2 rounded text-xs pointer-events-none opacity-0')
      .style('position', 'absolute')
      .style('z-index', '10')
      .style('visibility', 'hidden')
      .style('padding', '10px')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('border-radius', '4px')
      .style('color', '#fff');

    // Add circles for the nodes
    node.append('circle')
      .attr('r', 20)
      .attr('fill', d => nodeColors[d.type] || '#999')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('opacity', d => isRunning ? 0.9 : 0.7)
      .on('mouseover', function(event, d) {
        tooltip
          .style('visibility', 'visible')
          .style('opacity', 1)
          .html(`<strong>${d.name}</strong><br/>${d.type}<br/>${d.description || ''}`);
      })
      .on('mousemove', function(event) {
        tooltip
          .style('top', (event.pageY - 10) + 'px')
          .style('left', (event.pageX + 10) + 'px');
      })
      .on('mouseout', function() {
        tooltip.style('visibility', 'hidden').style('opacity', 0);
      });

    // Add pulsating effect for the active nodes when running
    if (isRunning) {
      node.append('circle')
        .attr('r', 20)
        .attr('fill', d => nodeColors[d.type] || '#999')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .attr('opacity', 0.3)
        .attr('class', 'pulse');
      
      // Add pulse animation
      const pulse = svg.selectAll('.pulse');
      repeat();
      
      function repeat() {
        pulse
          .transition()
          .duration(1000)
          .attr('r', 30)
          .attr('opacity', 0)
          .transition()
          .duration(1000)
          .attr('r', 20)
          .attr('opacity', 0.3)
          .on('end', repeat);
      }
    }

    // Add labels to the nodes
    node.append('text')
      .attr('dx', 0)
      .attr('dy', 30)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#fff')
      .text(d => d.name.length > 12 ? d.name.substring(0, 12) + '...' : d.name);

    // Define the tick function
    function ticked() {
      link
        .attr('x1', d => (d.source as any).x)
        .attr('y1', d => (d.source as any).y)
        .attr('x2', d => (d.target as any).x)
        .attr('y2', d => (d.target as any).y);
        
      linkLabels
        .attr('x', d => ((d.source as any).x + (d.target as any).x) / 2)
        .attr('y', d => ((d.source as any).y + (d.target as any).y) / 2);

      node
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
    }

    // Drag functions
    function dragstarted(event: d3.D3DragEvent<SVGGElement, Node, any>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, Node, any>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGGElement, Node, any>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [graphData, isRunning]);

  return (
    <div className="w-full h-full overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}