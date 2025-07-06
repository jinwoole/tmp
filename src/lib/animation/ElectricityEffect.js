import * as PIXI from 'pixi.js';

export class ElectricityEffect {
  constructor(app, nodeManager) {
    this.app = app;
    this.nodeManager = nodeManager;
    this.container = new PIXI.Container();
    this.app.stage.addChild(this.container);
    this.effects = [];
  }

  createEffect(startNodeId, endNodeId) {
    const startNode = this.nodeManager.getNode(startNodeId);
    const endNode = this.nodeManager.getNode(endNodeId);

    if (!startNode || !endNode) return;

    const particle = new PIXI.Graphics();
    const startPos = startNode.position;
    const endPos = endNode.position;

    // Change projectile color to blue
    particle.beginFill(0x00BFFF);
    particle.drawCircle(0, 0, 4); // Make particle a bit bigger
    particle.endFill();

    this.container.addChild(particle);

    const effect = {
      particle,
      progress: 0,
      duration: 0.25, // Increase speed (0.5 -> 0.25)
      startTime: Date.now(),
      getPoint(t) {
        // Change trajectory to a straight line (Linear interpolation)
        const x = (1 - t) * startPos.x + t * endPos.x;
        const y = (1 - t) * startPos.y + t * endPos.y;
        return { x, y };
      },
    };

    this.effects.push(effect);
  }

  animate() {
    const now = Date.now();
    for (let i = this.effects.length - 1; i >= 0; i--) {
      const effect = this.effects[i];
      const elapsed = (now - effect.startTime) / 1000;
      effect.progress = elapsed / effect.duration;

      if (effect.progress >= 1) {
        this.container.removeChild(effect.particle);
        this.effects.splice(i, 1);
      } else {
        const pos = effect.getPoint(effect.progress);
        effect.particle.position.set(pos.x, pos.y);
      }
    }
  }
}