<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue';

interface DropdownOption {
  value: string;
  label: string;
  rightLabel?: string;
  rightBadgeClass?: string;
  labelClass?: string;
}

const props = withDefaults(defineProps<{
  options: DropdownOption[];
  placeholder?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  label?: string;
  showClear?: boolean;
  clearLabel?: string;
  compact?: boolean;
}>(), {
  placeholder: 'Select option...',
  searchable: true,
  searchPlaceholder: 'Search...',
  label: '',
  showClear: false,
  clearLabel: '-- Clear Selection --',
  compact: false
});

const selectedValue = defineModel<string>({ required: true });

const isDropdownOpen = ref(false);
const searchQuery = ref('');
const buttonRef = ref<HTMLButtonElement | null>(null);
const dropdownStyle = ref<Record<string, string>>({});

const optionsMaxHeight = ref('300px');

const updatePosition = () => {
  if (!buttonRef.value) return;
  const rect = buttonRef.value.getBoundingClientRect();
  const estimatedHeight = 350; // Total estimated height of search + list
  const spaceBelow = window.innerHeight - rect.bottom;
  const spaceAbove = rect.top;

  if (spaceBelow < estimatedHeight && spaceAbove > spaceBelow) {
    // Show above the button
    const maxAvailable = Math.max(100, spaceAbove - 60);
    optionsMaxHeight.value = `${Math.min(300, maxAvailable - 60)}px`;
    dropdownStyle.value = {
      position: 'fixed',
      bottom: `${window.innerHeight - rect.top + 4}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`,
      zIndex: '9999'
    };
  } else {
    // Show below the button
    const maxAvailable = Math.max(100, spaceBelow - 60);
    optionsMaxHeight.value = `${Math.min(300, maxAvailable - 60)}px`;
    dropdownStyle.value = {
      position: 'fixed',
      top: `${rect.bottom + 4}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`,
      zIndex: '9999'
    };
  }
};

watch(isDropdownOpen, (isOpen) => {
  if (isOpen) {
    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);
  } else {
    window.removeEventListener('resize', updatePosition);
    window.removeEventListener('scroll', updatePosition, true);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updatePosition);
  window.removeEventListener('scroll', updatePosition, true);
});

const selectedOption = computed(() => {
  return props.options.find(o => o.value === selectedValue.value);
});

const filteredOptions = computed(() => {
  if (!props.searchable || !searchQuery.value.trim()) {
    return props.options;
  }
  const q = searchQuery.value.toLowerCase();
  return props.options.filter(o => 
    o.label.toLowerCase().includes(q) || 
    o.value.toLowerCase().includes(q) || 
    (o.rightLabel && o.rightLabel.toLowerCase().includes(q))
  );
});

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value;
  searchQuery.value = '';
};

const selectOption = (val: string) => {
  selectedValue.value = val;
  isDropdownOpen.value = false;
};
</script>

<template>
  <div :class="compact ? 'relative' : 'form-group relative'">
    <label v-if="label">{{ label }}</label>
    <div class="relative w-full">
      <button 
        ref="buttonRef"
        type="button" 
        @click="toggleDropdown" 
        class="w-full border border-border-color rounded-sm bg-bg-secondary text-text-primary flex justify-between items-center cursor-pointer outline-none transition-all duration-150 ease-in-out text-left focus:border-accent focus:shadow-[0_0_0_3px] focus:shadow-accent-light"
        :class="compact ? 'py-1 px-2 text-[0.8rem]' : 'py-3 px-4 text-sm'"
      >
        <span v-if="selectedOption" class="truncate pr-2" :class="selectedOption.labelClass">
          {{ selectedOption.label }}
        </span>
        <span v-else style="color: var(--text-tertiary);" class="truncate pr-2">
          {{ placeholder }}
        </span>

        <span v-if="selectedOption && selectedOption.rightLabel" 
          class="font-bold uppercase py-0.5 px-1.5 rounded-[4px] tracking-wide ml-auto mr-2 shrink-0" 
          :class="[
            selectedOption.rightBadgeClass || 'bg-slate-100 text-slate-600',
            compact ? 'text-[0.625rem]' : 'text-[0.65rem]'
          ]"
        >
          {{ selectedOption.rightLabel }}
        </span>

        <span class="text-text-tertiary text-[0.75rem] shrink-0">&#9662;</span>
      </button>

      <!-- Dropdown Options Panel (Teleported to body for absolute overlay precedence) -->
      <Teleport to="body">
        <div v-if="isDropdownOpen" class="fixed inset-0 w-screen h-screen z-[9990] bg-transparent" @click="isDropdownOpen = false"></div>
        <div 
          v-if="isDropdownOpen" 
          :style="dropdownStyle"
          class="mt-1 bg-bg-secondary border border-border-color rounded-sm shadow-lg p-2 flex flex-col gap-2 animate-[fadeIn_0.1s_ease-out]"
        >
          <input 
            v-if="searchable"
            type="text" 
            v-model="searchQuery" 
            class="form-control" 
            :class="compact ? 'text-[0.8rem] py-1 px-2 mb-1' : 'text-sm p-2'"
            :placeholder="searchPlaceholder"
            @click.stop
          />
          <div 
            :style="{ maxHeight: optionsMaxHeight }"
            class="overflow-y-auto flex flex-col gap-0.5"
          >
            <div 
              v-if="showClear"
              @click="selectOption('')" 
              class="cursor-pointer rounded-[4px] flex justify-between items-center transition-colors duration-150 ease-in-out hover:bg-bg-tertiary"
              :class="[
                selectedValue === '' ? 'bg-accent-light text-accent' : '',
                compact ? 'text-[0.8rem] py-1 px-2' : 'text-sm py-2 px-3'
              ]"
            >
              <span style="color: var(--text-tertiary);">{{ clearLabel }}</span>
            </div>

            <div 
              v-for="opt in filteredOptions" 
              :key="opt.value"
              @click="selectOption(opt.value)" 
              class="cursor-pointer rounded-[4px] flex justify-between items-center transition-colors duration-150 ease-in-out hover:bg-bg-tertiary"
              :class="[
                selectedValue === opt.value ? 'bg-accent-light text-accent font-semibold' : '',
                compact ? 'text-[0.8rem] py-1 px-2' : 'text-sm py-2 px-3'
              ]"
            >
              <span class="truncate pr-2" :class="opt.labelClass">{{ opt.label }}</span>
              <span v-if="opt.rightLabel" 
                class="font-bold uppercase py-0.5 px-1.5 rounded-[4px] tracking-wide shrink-0" 
                :class="[
                  opt.rightBadgeClass || 'bg-slate-100 text-slate-600',
                  compact ? 'text-[0.625rem]' : 'text-[0.65rem]'
                ]"
              >
                {{ opt.rightLabel }}
              </span>
            </div>

            <div v-if="filteredOptions.length === 0" style="padding: 1rem; text-align: center; color: var(--text-tertiary); font-size: 0.8rem;">
              No options match query.
            </div>
          </div>
        </div>
      </Teleport>
    </div>
  </div>
</template>
