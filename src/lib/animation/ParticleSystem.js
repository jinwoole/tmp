import * as PIXI from 'pixi.js';

class Particle {
  constructor(x, y, container) {
    this.graphic = new PIXI.Graphics();
    // Use the new orange accent color
    this.graphic.beginFill(0x00BFFF); // Change color to blue
    this.graphic.drawCircle(0, 0, Math.random() * 1.5 + 0.5);
    this.graphic.endFill();
    this.graphic.x = x;
    this.graphic.y = y;

    // Increase particle speed
    this.vx = (Math.random() - 0.5) * 4; // Increased speed
    this.vy = (Math.random() - 0.5) * 4; // Increased speed
    this.alpha = 1;
    this.lifetime = Math.random() * 0.5 + 0.2;
    this.age = 0;

    container.addChild(this.graphic);
  }

  update(delta) {
    this.graphic.x += this.vx * delta;
    this.graphic.y += this.vy * delta;
    this.age += delta / 60; // Assuming 60 FPS
    this.graphic.alpha = 1 - (this.age / this.lifetime);

    return this.age < this.lifetime;
  }

  destroy() {
    this.graphic.destroy();
  }
}

export class ParticleSystem {
  constructor(app) {
    this.app = app;
    this.container = new PIXI.Container();
    this.app.stage.addChild(this.container);
    this.particles = [];
  }

  emit(x, y, count = 20) {
    for (let i = 0; i < count; i++) {
      this.particles.push(new Particle(x, y, this.container));
    }
  }

  animate(delta) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      if (!this.particles[i].update(delta)) {
        this.particles[i].destroy();
        this.particles.splice(i, 1);
      }
    }
  }
}