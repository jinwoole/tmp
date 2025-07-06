<script>
  import { vms, events } from '$lib/store.js';

  // Helper to format numbers
  const formatNumber = (num) => num.toLocaleString();

  let totalRequests = 0;
  $: totalRequests = $events.length;
</script>

<!-- Clean, modern stats panel -->
<div class="bg-[#1C1C1E] p-6 rounded-xl h-full flex flex-col">
  <h2 class="text-2xl font-light text-white mb-6">Network Stats</h2>
  
  <div class="mb-8">
    <div class="text-sm text-gray-400 mb-1">Total Requests</div>
    <div class="text-4xl font-medium text-white">{formatNumber(totalRequests)}</div>
  </div>

  <div class="space-y-5 flex-grow overflow-y-auto">
    {#each Array.from($vms.values()) as vm (vm.id)}
      <div class="bg-[#2C2C2E] p-4 rounded-lg">
        <div class="flex justify-between items-center mb-2">
          <span class="font-medium text-white truncate pr-2">{vm.id}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-400 capitalize">{vm.status}</span>
            <div class="w-2.5 h-2.5 rounded-full"
                 class:bg-orange-500={vm.status === 'active'}
                 class:bg-gray-500={vm.status !== 'active'}>
            </div>
          </div>
        </div>
        
        <div class="text-xs text-gray-500 mb-3">
          {vm.ips.size} unique source IPs
        </div>

        <div>
          <div class="flex justify-between text-xs text-gray-400 mb-1">
            <span>Load</span>
            <span>{vm.load.toFixed(0)}%</span>
          </div>
          <div class="w-full bg-gray-700 rounded-full h-1.5">
            <div class="bg-orange-500 h-1.5 rounded-full transition-all duration-300"
                 style="width: {vm.load}%;">
            </div>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>