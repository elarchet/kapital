<script lang="ts">
// Module-scoped: shared across all instances, no re-allocation per component
const CATEGORIES = [
  {
    id: 'people',
    name: 'People & Gestures',
    icon: '👋',
    emojis: [
      '👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤌', '🤏', '✌️', '🤞', '🫰', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '✍️', '💅', '🤳', '💪', '🦾', '🦿', '🦵', '🦶', '👂', '🦻', '👃', '🧠', '👀', '👁️', '👅', '👄', '💋', '👤', '👥', '🧑', '👧', '👦', '👩', '👨', '👵', '👴', '👮', '🕵️', '💂', '👷', '🤴', '👸', '🦸', '🦹', '🧙', '🧚', '🧛', '🧜', '🧝', '🧞', '🧟', '🧌', '🧑‍💼', '🧑‍🔬', '🧑‍🎨', '🧑‍🏫', '🧑‍⚕️', '🧑‍🚀', '🧑‍✈️'
    ]
  },
  {
    id: 'finance',
    name: 'Finance & Work',
    icon: '💰',
    emojis: [
      '💼', '💰', '🪙', '📈', '📉', '🏦', '💵', '💴', '💶', '💷', '💸', '💳', '🧾', '💎', '⚖️', '📊', '📅', '📆', '🗓️', '📁', '📂', '🗂️', '🗃️', '🗒️', '📝', '✏️', '✒️', '🖋️', '🖊️', '📎', '🖇️', '📐', '📏', '📌', '📍', '🔒', '🔓', '🔏', '🔐', '🔑', '🗝️', '⚙️', '🛠️', '🧰', '🔩', '🧱', '🪜', '📬', '📮', '📯', '📣', '🔔', '🔕', '📲', '💬', '🗨️', '🗯️', '💭', '🔖', '🏷️', '📦', '🛒', '🏪', '🏬', '🏭', '🏢', '🏣', '🏤', '🏥', '🏦', '🏨', '🏩'
    ]
  },
  {
    id: 'nature',
    name: 'Animals & Nature',
    icon: '🦁',
    emojis: [
      '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🦆', '🦅', '🦉', '🦇', '🐺', '🐴', '🦄', '🐝', '🦋', '🐞', '🦟', '🦗', '🕷️', '🦂', '🐢', '🐍', '🦎', '🐙', '🦑', '🦞', '🦀', '🐠', '🐟', '🐬', '🐳', '🐋', '🦈', '🐊', '🐅', '🐆', '🦓', '🦍', '🐘', '🦛', '🦏', '🦒', '🦬', '🐃', '🐂', '🐄', '🦙', '🐐', '🦌', '🦝', '🦨', '🦡', '🦦', '🦥', '🐾', '🐉', '🐲', '🌵', '🎄', '🌲', '🌳', '🌴', '🌱', '🌿', '☘️', '🍀', '🍁', '🍂', '🍃', '🍄', '🌰', '🌾', '🌺', '🌸', '🌼', '🌻', '🌹', '🌷', '🌱'
    ]
  },
  {
    id: 'food',
    name: 'Food & Drink',
    icon: '🍕',
    emojis: [
      '🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🫐', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶️', '🫑', '🌽', '🥕', '🧄', '🧅', '🥔', '🍠', '🥐', '🥯', '🍞', '🥖', '🧀', '🥚', '🍳', '🥞', '🧇', '🥓', '🥩', '🍗', '🍖', '🌭', '🍔', '🍟', '🍕', '🌮', '🌯', '🫔', '🥗', '🥘', '🍲', '🥣', '🍿', '🧈', '🍚', '🍛', '🍜', '🍝', '🍣', '🍤', '🍥', '🍡', '🥟', '🥡', '🍦', '🍧', '🍨', '🍩', '🍪', '🎂', '🍰', '🧁', '🥧', '🍫', '🍬', '🍭', '🍯', '🥛', '☕', '🫖', '🍵', '🍶', '🍾', '🍷', '🍸', '🍹', '🍺', '🍻', '🥂', '🥃', '🥤', '🧋', '🧃', '🧊'
    ]
  },
  {
    id: 'travel',
    name: 'Travel & Places',
    icon: '🚗',
    emojis: [
      '🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🛻', '🚚', '🚛', '🚜', '🚲', '🛴', '🏍️', '🛵', '🚨', '🚃', '🚋', '🚄', '🚅', '🚈', '🚊', '🚇', '🚀', '🛸', '🚁', '✈️', '🛫', '🛬', '🛰️', '⛵', '🛥️', '🚤', '🛳️', '⛴️', '🚢', '⚓', '🏔️', '⛰️', '🌋', '🗻', '🏕️', '⛺', '🛖', '🏠', '🏡', '🏰', '💒', '🗼', '🗽', '⛪', '🕌', '🛕', '⛩️', '🕋', '⛲', '🌁', '🌃', '🏙️', '🌄', '🌅', '🌆', '🌇', '🌉', '🎡', '🎢', '🏖️', '🏜️', '🏝️', '🏞️', '🌍', '🌎', '🌏', '🌐', '🗺️', '🧭', '🌅', '🌄'
    ]
  },
  {
    id: 'activities',
    name: 'Activities & Sports',
    icon: '🎮',
    emojis: [
      '⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🛹', '🛼', '🎯', '🎱', '🎮', '🕹️', '🎰', '🎲', '🧩', '🎳', '🥊', '🥋', '🎽', '🏂', '⛷️', '🪂', '🚴', '🏃', '🚶', '🧗', '🧘', '🏊', '🚣', '🎪', '🎭', '🎨', '🎬', '🎤', '🎧', '🎼', '🎹', '🥁', '🎷', '🎺', '🎸', '🪕', '🎻', '🎟️', '🎫', '🏆', '🥇', '🥈', '🥉', '🏅', '🎖️', '🎗️', '🏵️', '🎁', '🎀', '🎊', '🎉', '🪄', '🎭', '🎈'
    ]
  },
  {
    id: 'objects',
    name: 'Objects & Tech',
    icon: '💡',
    emojis: [
      '⌚', '📱', '📲', '💻', '⌨️', '🖥️', '🖨️', '🖱️', '🕹️', '💽', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽️', '🎞️', '📞', '☎️', '📺', '📻', '🎙️', '🎚️', '🎛️', '🧭', '⏱️', '⏲️', '⏰', '⏳', '⌛', '📡', '🔋', '🔌', '💡', '🔦', '🕯️', '🪔', '🧯', '🛢️', '🔑', '🗝️', '🔐', '🔏', '🔒', '🔓', '🔮', '📿', '🧿', '💈', '⚗️', '🔭', '🔬', '🩹', '🩺', '💊', '💉', '🧬', '🦠', '🧫', '🧪', '🌡️', '🧹', '🧺', '🧻', '🧼', '🧽', '🪣', '🛁', '🚿', '🪒', '🧴', '🪥', '🧲', '🪝', '🪤'
    ]
  },
  {
    id: 'symbols',
    name: 'Symbols & Hearts',
    icon: '❤️',
    emojis: [
      '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️', '✝️', '☪️', '🕉️', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '⛎', '🔀', '🔁', '🔂', '▶️', '⏩', '⏭️', '◀️', '⏪', '⏮️', '🔼', '🔽', '⏸️', '⏹️', '⏺️', '➕', '➖', '✖️', '➗', '♾️', '‼️', '⁉️', '❓', '❔', '⚠️', '🚸', '⛔', '🚫', '✅', '❌', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '🔶', '🔷', '🔸', '🔹', '🔺', '🔻', '💠', '🔘', '🔲', '🔳', '⬛', '⬜', '◼', '◻', '◾', '◽', '▪', '▫', '🆗', '🆙', '🆓'
    ]
  }
];

import { ref } from 'vue';

// Module-scoped singleton: only one picker open at a time across ALL instances
const activePicker = ref<symbol | null>(null);
</script>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { Folder } from '@lucide/vue';

const props = defineProps<{
  modelValue: string | null;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void;
}>();

// Unique identity for this instance
const instanceId = Symbol();

const isOpen = computed(() => activePicker.value === instanceId);
const triggerRef = ref<HTMLElement | null>(null);
const activeTab = ref('finance');
const customInput = ref('');

// Fixed position coords for the teleported popover
const popoverStyle = computed(() => {
  if (!triggerRef.value || !isOpen.value) return {};
  const rect = triggerRef.value.getBoundingClientRect();
  return {
    position: 'fixed' as const,
    top: `${rect.top}px`,
    left: `${rect.right + 8}px`,
    zIndex: 9999,
  };
});

const toggleOpen = (e: MouseEvent) => {
  if (props.disabled) return;
  e.stopPropagation();
  e.preventDefault();
  activePicker.value = isOpen.value ? null : instanceId;
  if (isOpen.value) {
    customInput.value = props.modelValue || '';
  }
};

const selectEmoji = (emoji: string | null) => {
  emit('update:modelValue', emoji);
  activePicker.value = null;
};

const handleCustomInput = (val: string) => {
  customInput.value = val;
  emit('update:modelValue', val.trim() || null);
};

const onWindowClick = (e: MouseEvent) => {
  if (!isOpen.value) return;
  if (triggerRef.value && triggerRef.value.contains(e.target as Node)) return;
  const popover = document.getElementById('emoji-popover-active');
  if (popover && popover.contains(e.target as Node)) return;
  activePicker.value = null;
};

onMounted(() => {
  window.addEventListener('click', onWindowClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', onWindowClick);
});
</script>

<template>
  <div ref="triggerRef" class="relative flex items-center justify-center flex-shrink-0">
    <button 
      @click="toggleOpen($event)"
      class="w-5 h-5 flex items-center justify-center rounded text-sm border-0 bg-transparent p-0"
      :class="disabled ? 'cursor-default' : 'hover:bg-bg-tertiary cursor-pointer transition-colors'"
      :title="disabled ? undefined : 'Set emoji'"
    >
      <span v-if="modelValue" class="text-sm leading-none select-none">{{ modelValue }}</span>
      <Folder v-else class="nav-icon !mr-0 !w-4 !h-4 text-text-secondary" />
    </button>

    <!-- Teleport to body to escape sidebar overflow clipping -->
    <Teleport to="body">
      <div 
        v-if="isOpen"
        id="emoji-popover-active"
        :style="popoverStyle"
        class="w-64 bg-bg-secondary border border-border-color rounded-md shadow-lg p-3 flex flex-col"
        @click.stop
        @mousedown.stop
      >
        <!-- Custom Text Input -->
        <input 
          type="text" 
          :value="customInput"
          placeholder="Paste or type any emoji (OS shortcut)" 
          class="w-full bg-bg-tertiary border border-border-color rounded px-2.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent text-center font-sans mb-2"
          maxlength="8"
          @input.stop="handleCustomInput(($event.target as HTMLInputElement).value)"
          @click.stop
        />

        <!-- Category Tabs -->
        <div 
          class="flex gap-1 overflow-x-auto pb-1.5 mb-1.5 border-b border-border-color scrollbar-none"
          @click.stop
        >
          <button 
            v-for="cat in CATEGORIES" 
            :key="cat.id"
            @click.stop.prevent="activeTab = cat.id"
            @mousedown.stop.prevent
            class="px-1.5 py-1 rounded text-sm transition-colors border-0 bg-transparent cursor-pointer flex-shrink-0"
            :class="activeTab === cat.id ? 'bg-bg-tertiary ring-1 ring-border-color opacity-100' : 'opacity-50 hover:opacity-80'"
            :title="cat.name"
          >
            {{ cat.icon }}
          </button>
        </div>

        <!-- Emoji Grid -->
        <div 
          class="grid grid-cols-7 gap-0.5 max-h-40 overflow-y-auto scrollbar-thin mb-2"
          @click.stop
        >
          <template v-for="cat in CATEGORIES" :key="cat.id">
            <template v-if="activeTab === cat.id">
              <button 
                v-for="em in cat.emojis" 
                :key="em"
                @click.stop.prevent="selectEmoji(em)"
                @mousedown.stop
                class="hover:bg-bg-tertiary p-0.5 rounded text-base cursor-pointer border-0 bg-transparent flex items-center justify-center transition-all hover:scale-125 select-none"
              >
                {{ em }}
              </button>
            </template>
          </template>
        </div>

        <!-- Clear Action -->
        <button 
          @click.stop.prevent="selectEmoji(null)"
          @mousedown.stop
          class="w-full hover:bg-bg-tertiary py-1.5 rounded text-xs text-text-secondary cursor-pointer border border-border-color transition-colors"
        >
          Clear Emoji ❌
        </button>
      </div>
    </Teleport>
  </div>
</template>
