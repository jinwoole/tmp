<script>
  import { onMount, onDestroy } from 'svelte';
  import * as PIXI from 'pixi.js';
  import { NodeManager } from '$lib/animation/NodeManager.js';
  import { ElectricityEffect } from '$lib/animation/ElectricityEffect.js';
  import { ParticleSystem } from '$lib/animation/ParticleSystem.js';
  import { events, vms } from '$lib/store.js';

  let canvasContainer;
  let app;
  let nodeManager;
  let electricityEffect;
  let particleSystem;
  let lastEventCount = 0;

  onMount(async () => {
    app = new PIXI.Application();

    await app.init({
      width: canvasContainer.clientWidth,
      height: canvasContainer.clientHeight,
      backgroundColor: 0x0a0a0a,
      resizeTo: canvasContainer,
      antialias: true,
    });

    canvasContainer.appendChild(app.canvas);
    nodeManager = new NodeManager(app);
    nodeManager.initializeBaseNodes(app.screen.width, app.screen.height);
    electricityEffect = new ElectricityEffect(app, nodeManager);
    particleSystem = new ParticleSystem(app);

    app.ticker.add((delta) => {
      electricityEffect.animate();
      particleSystem.animate(delta);
    });

    return () => {
      app.destroy(true, { children: true, texture: true, baseTexture: true });
    };
  });

  // Update VM nodes when the vms map changes
  $: if (nodeManager && $vms) {
    nodeManager.updateVMNodes($vms, app.screen.width, app.screen.height);
  }

  // Optimized reactive statement to trigger animations only for new events
  $: {
    if (app && electricityEffect && particleSystem && $events.length > lastEventCount) {
      const newEvents = $events.slice(lastEventCount);
      newEvents.forEach(event => {
        if (!nodeManager.getNode(event.vmId)) return; // Ensure VM node exists

        // 1. Animate from Client to Load Balancer
        electricityEffect.createEffect('client', 'loadBalancer');
        
        const effectDuration = 250; // Corresponds to duration in ElectricityEffect.js

        // 2. After the first animation, animate from LB to VM
        setTimeout(() => {
          if (!nodeManager.getNode(event.vmId)) return; // Re-check node exists

          const lbNode = nodeManager.getNode('loadBalancer');
          if (lbNode) particleSystem.emit(lbNode.x, lbNode.y); // Particle effect at LB

          electricityEffect.createEffect('loadBalancer', event.vmId);

          // 3. After the second animation, show particle effect at the VM
          setTimeout(() => {
            if (!nodeManager.getNode(event.vmId)) return; // Re-check node exists
            const vmNode = nodeManager.getNode(event.vmId);
            if (vmNode) particleSystem.emit(vmNode.x, vmNode.y);
          }, effectDuration);

        }, effectDuration);
      });
    }
    lastEventCount = $events.length;
  }
</script>

<div bind:this={canvasContainer} class="w-full h-full rounded-lg border border-gray-700 overflow-hidden bg-black"></div>