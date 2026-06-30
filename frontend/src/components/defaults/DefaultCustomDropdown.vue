<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue';

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
const searchInputRef = ref<HTMLInputElement | null>(null);
const optionsContainerRef = ref<HTMLDivElement | null>(null);
const dropdownStyle = ref<Record<string, string>>({});
const highlightedIndex = ref(0);

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

const focusSearchInput = () => {
  nextTick(() => {
    if (searchInputRef.value) {
      searchInputRef.value.focus();
    }
  });
};

watch(isDropdownOpen, (isOpen) => {
  if (isOpen) {
    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);
    focusSearchInput();
  } else {
    window.removeEventListener('resize', updatePosition);
    window.removeEventListener('scroll', updatePosition, true);
    searchQuery.value = '';
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
  if (!searchQuery.value.trim()) {
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

const resetHighlightedIndex = () => {
  if (filteredOptions.value.length === 0) {
    highlightedIndex.value = -1;
    return;
  }
  const selectedIdx = filteredOptions.value.findIndex(o => o.value === selectedValue.value);
  if (selectedIdx !== -1) {
    highlightedIndex.value = selectedIdx;
  } else {
    highlightedIndex.value = 0;
  }
};

watch(filteredOptions, () => {
  resetHighlightedIndex();
}, { immediate: true });

const scrollHighlightedIntoView = () => {
  nextTick(() => {
    if (!optionsContainerRef.value) return;
    const activeEl = optionsContainerRef.value.querySelector(
      `[data-option-index="${highlightedIndex.value}"]`
    ) as HTMLElement;
    if (activeEl && activeEl.scrollIntoView) {
      activeEl.scrollIntoView({ block: 'nearest' });
    }
  });
};

const navigateOptions = (direction: 'up' | 'down') => {
  if (!isDropdownOpen.value) {
    isDropdownOpen.value = true;
    return;
  }
  const len = filteredOptions.value.length;
  if (len === 0) return;

  if (direction === 'down') {
    highlightedIndex.value = (highlightedIndex.value + 1) % len;
  } else {
    highlightedIndex.value = (highlightedIndex.value - 1 + len) % len;
  }
  scrollHighlightedIntoView();
};

const selectHighlightedOption = () => {
  if (isDropdownOpen.value && highlightedIndex.value >= 0 && highlightedIndex.value < filteredOptions.value.length) {
    selectOption(filteredOptions.value[highlightedIndex.value].value);
  }
};

const closeDropdown = () => {
  isDropdownOpen.value = false;
  buttonRef.value?.focus();
};

const onInputKeydown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    e.stopPropagation();
    navigateOptions('down');
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    e.stopPropagation();
    navigateOptions('up');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    e.stopPropagation();
    selectHighlightedOption();
  } else if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    closeDropdown();
  }
};

const onButtonKeydown = (e: KeyboardEvent) => {
  // If user presses Enter
  if (e.key === 'Enter') {
    e.preventDefault();
    if (isDropdownOpen.value) {
      selectHighlightedOption();
    } else {
      isDropdownOpen.value = true;
    }
    return;
  }

  // If user presses Escape
  if (e.key === 'Escape') {
    e.preventDefault();
    closeDropdown();
    return;
  }

  // If user presses Space
  if (e.key === ' ' || e.key === 'Spacebar') {
    e.preventDefault();
    if (!isDropdownOpen.value) {
      isDropdownOpen.value = true;
    }
    return;
  }

  // Arrow navigation on button
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    navigateOptions('down');
    return;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    navigateOptions('up');
    return;
  }

  // Handle first letter / alphanumeric filtering when tapping printable characters
  if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    if (!isDropdownOpen.value) {
      isDropdownOpen.value = true;
    }
    if (props.searchable) {
      searchQuery.value = e.key;
      focusSearchInput();
    } else {
      searchQuery.value += e.key;
    }
  }

  // If searchable is false, handle Backspace to delete last character from query
  if (e.key === 'Backspace' && !props.searchable) {
    e.preventDefault();
    searchQuery.value = searchQuery.value.slice(0, -1);
  }
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
        @keydown="onButtonKeydown"
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
            ref="searchInputRef"
            type="text" 
            v-model="searchQuery" 
            class="form-control" 
            :class="compact ? 'text-[0.8rem] py-1 px-2 mb-1' : 'text-sm p-2'"
            :placeholder="searchPlaceholder"
            @click.stop
            @keydown="onInputKeydown"
          />
          <div 
            ref="optionsContainerRef"
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
              v-for="(opt, index) in filteredOptions" 
              :key="opt.value"
              :data-option-index="index"
              @click="selectOption(opt.value)" 
              @mouseenter="highlightedIndex = index"
              class="cursor-pointer rounded-[4px] flex justify-between items-center transition-colors duration-150 ease-in-out hover:bg-bg-tertiary"
              :class="[
                selectedValue === opt.value ? 'text-accent font-semibold' : '',
                highlightedIndex === index ? 'bg-bg-tertiary' : (selectedValue === opt.value ? 'bg-accent-light' : ''),
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
