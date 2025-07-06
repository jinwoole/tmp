import * as PIXI from 'pixi.js';

// Clean, Apple-inspired color palette
const NODE_STYLES = {
  client: { fill: 0x999999, radius: 20 }, // Muted gray
  loadBalancer: { fill: 0xCCCCCC, radius: 30 }, // Light gray
  vm: { fill: 0xFF9500, radius: 25 }, // Apple's vibrant orange
};

export class NodeManager {
  constructor(app) {
    this.app = app;
    this.nodes = new Map();
    this.container = new PIXI.Container();
    this.app.stage.addChild(this.container);
  }

  createNode(id, type, position) {
    const style = NODE_STYLES[type];
    const node = new PIXI.Graphics();
    node.id = id; // Store id for later reference
    node.type = type; // Store type for later reference

    node.beginFill(style.fill);
    node.drawCircle(0, 0, style.radius);
    node.endFill();
    node.position.set(position.x, position.y);

    const label = new PIXI.Text(id, { fontSize: 14, fill: 0xffffff, align: 'center' });
    label.anchor.set(0.5);
    label.position.set(0, style.radius + 15);
    node.addChild(label);

    this.nodes.set(id, node);
    this.container.addChild(node);
    return node;
  }

  getNode(id) {
    return this.nodes.get(id);
  }

  updateVMNodes(vms, width, height) {
    const vmIds = new Set(Array.from(vms.values()).map(vm => vm.id));
    const vmCount = vmIds.size;
    const yPadding = height * 0.2; // 20% padding top and bottom
    const availableHeight = height - yPadding * 2;
    const xPosition = width * 0.8; // Move VMs to the right

    // Add or update nodes
    let i = 0;
    for (const vmId of vmIds) {
      if (!this.nodes.has(vmId)) {
        // Distribute VMs vertically with improved spacing
        const y = vmCount > 1 
          ? yPadding + (i * (availableHeight / (vmCount - 1)))
          : height / 2; // Center if only one VM
        this.createNode(vmId, 'vm', { x: xPosition, y });
      }
      i++;
    }

    // Remove old nodes by checking their type
    const nodesToRemove = [];
    for(const node of this.container.children) {
        if (node.type === 'vm' && !vmIds.has(node.id)) {
            nodesToRemove.push(node);
        }
    }

    for (const node of nodesToRemove) {
        this.nodes.delete(node.id);
        this.container.removeChild(node);
        node.destroy();
    }
  }

  // Initialize static nodes like client and load balancer
  initializeBaseNodes(width, height) {
    this.createNode('client', 'client', { x: width * 0.15, y: height / 2 });
    this.createNode('loadBalancer', 'loadBalancer', { x: width * 0.45, y: height / 2 });
  }
}