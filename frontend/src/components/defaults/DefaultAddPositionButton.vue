<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { Plus } from '@lucide/vue';

const emit = defineEmits<{
  (e: 'open-manual'): void;
  (e: 'open-import'): void;
}>();

const showDropdown = ref(false);

const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value;
};

const openManual = () => {
  showDropdown.value = false;
  emit('open-manual');
};

const openImport = () => {
  showDropdown.value = false;
  emit('open-import');
};

const closeDropdown = (e: MouseEvent) => {
  const el = document.getElementById('btn-add-position-component');
  if (el && !el.contains(e.target as Node)) {
    showDropdown.value = false;
  }
};

onMounted(() => {
  window.addEventListener('click', closeDropdown);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', closeDropdown);
});
</script>

<template>
  <div style="position: relative; display: inline-block;">
    <button 
      @click.stop="toggleDropdown" 
      class="btn btn-primary" 
      id="btn-add-position-component"
    >
      <Plus style="width: 16px; height: 16px;" />
      <span>Add Position</span>
    </button>
    <div 
      v-if="showDropdown" 
      class="dropdown-menu card" 
      style="position: absolute; right: 0; top: 110%; z-index: 100; min-width: 160px; padding: 0.5rem; display: flex; flex-direction: column; gap: 0.25rem;"
    >
      <button @click="openManual" class="bg-transparent border-0 py-2 px-4 text-left text-sm font-medium text-text-primary rounded-sm cursor-pointer transition-colors duration-150 ease-in-out w-full hover:bg-bg-tertiary">Manual Entry</button>
      <button @click="openImport" class="bg-transparent border-0 py-2 px-4 text-left text-sm font-medium text-text-primary rounded-sm cursor-pointer transition-colors duration-150 ease-in-out w-full hover:bg-bg-tertiary">Import File</button>
    </div>
  </div>
</template>
