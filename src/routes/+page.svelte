<script>
  import StatsPanel from '$lib/components/StatsPanel.svelte';
  import NetworkCanvas from '$lib/components/NetworkCanvas.svelte';
  import '$lib/store.js'; // Import to initialize the store
</script>

<main class="text-gray-300 min-h-screen p-8">
  <h1 class="text-4xl font-light text-white text-center mb-8">
    Real-Time Load Balancer Visualization
  </h1>
  <div class="flex flex-col lg:flex-row gap-8 max-w-screen-xl mx-auto">
    <div class="w-full lg:w-1/4">
      <StatsPanel />
    </div>
    <div class="w-full lg:w-3/4 h-[75vh]">
      <NetworkCanvas />
    </div>
  </div>
</main>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap');

  :global(body) {
    background-color: #121212; /* A modern, clean dark background */
    font-family: 'Inter', sans-serif;
  }
</style>
