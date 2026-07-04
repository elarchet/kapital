<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useKapitalStore } from '../../store';
import { api } from '../../services/api';
import { 
  LayoutDashboard, 
  LogOut, 
  PlusCircle, 
  Folder,
  Loader,
  ChevronLeft,
  ChevronRight,
  Settings,
  ChevronUp
} from '@lucide/vue';
import { SIDEBAR_CONFIG } from '../../config/sidebar';
import EmojiPicker from '../portfolio/EmojiPicker.vue';

const router = useRouter();
const route = useRoute();
const store = useKapitalStore();

const isSubmitting = ref(false);
const submitError = ref('');

// Rename states
const editingPortfolioId = ref<number | null>(null);
const editingName = ref('');
const renameInput = ref<HTMLInputElement[] | null>(null);

// Drag and drop states
const dragSrcId = ref<number | null>(null);
const dragTargetIdx = ref<number | null>(null);

const onDragStart = (e: DragEvent, id: number) => {
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(id));
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    e.dataTransfer.setDragImage(canvas, 0, 0);
  }
  setTimeout(() => { dragSrcId.value = id; }, 0);
};

const onContainerDragOver = (e: DragEvent) => {
  e.preventDefault();
  if (dragSrcId.value === null) return;

  const container = e.currentTarget as HTMLElement;
  // Get all children except the one currently being dragged (which has opacity-25/is visually moving)
  // or simply filter out the dragged node using its ID or checking dragSrcId.
  const items = (Array.from(container.children) as HTMLElement[]).filter(item => {
    // If it's the element being dragged, exclude it from position checking to prevent layout shifting midpoints
    return !item.classList.contains('opacity-25');
  });

  const srcIndex = store.portfolios.findIndex(p => p.id === dragSrcId.value);
  if (srcIndex === -1) return;

  let newIdx = items.length;
  for (let i = 0; i < items.length; i++) {
    const rect = items[i].getBoundingClientRect();
    const mid = rect.top + rect.height / 2;
    if (e.clientY < mid) {
      newIdx = i;
      break;
    }
  }

  // Adjust target index based on original source position
  // Because the dragged item is excluded, if newIdx is after the current position,
  // we adjust by 0 or 1 to match the correct store index mapping.
  let targetIdx = newIdx;
  if (targetIdx > srcIndex) {
    // Since we filtered it out, the target index maps to one slot higher in the full array
  }

  if (dragTargetIdx.value === targetIdx) return;
  dragTargetIdx.value = targetIdx;

  if (srcIndex === targetIdx) return;

  const order = store.portfolios.map(p => p.id);
  const [moved] = order.splice(srcIndex, 1);
  order.splice(targetIdx, 0, moved);
  store.updatePortfoliosOrder(order);
};

const onDragEnd = () => {
  dragSrcId.value = null;
  dragTargetIdx.value = null;
};

const handleLogout = () => {
  api.logout();
  store.setAuthenticated(false);
  router.push('/login');
};

const startRename = (p: any) => {
  editingPortfolioId.value = p.id;
  editingName.value = p.name;
};

const cancelRename = () => {
  editingPortfolioId.value = null;
  editingName.value = '';
};

const saveRename = async (id: number) => {
  const trimmed = editingName.value.trim();
  if (!trimmed) {
    cancelRename();
    return;
  }
  try {
    await store.updatePortfolio(id, { name: trimmed });
  } catch (err) {
    console.error('Failed to rename portfolio:', err);
  } finally {
    editingPortfolioId.value = null;
  }
};

const handleDirectCreatePortfolio = async () => {
  isSubmitting.value = true;
  submitError.value = '';
  try {
    const count = store.portfolios.length + 1;
    const name = `New Portfolio ${count}`;
    const newPtf = await store.createPortfolio(name, '');
    
    await router.push({
      path: `/portfolio/${newPtf.id}`,
      state: { editNameInline: true }
    });
    editingPortfolioId.value = newPtf.id;
    editingName.value = newPtf.name;
  } catch (err: any) {
    submitError.value = err.message || 'Failed to create portfolio';
  } finally {
    isSubmitting.value = false;
  }
};

watch(editingPortfolioId, async (newVal) => {
  if (newVal !== null) {
    await nextTick();
    if (renameInput.value && renameInput.value.length > 0) {
      const el = renameInput.value[0];
      el.focus();
      el.select();
    }
  }
});

const updateSidebarWidthProperty = () => {
  const width = store.sidebarCollapsed 
    ? `${SIDEBAR_CONFIG.COLLAPSED_WIDTH}px` 
    : `${store.sidebarWidth}px`;
  document.documentElement.style.setProperty('--sidebar-width', width);
};

watch(() => [store.sidebarWidth, store.sidebarCollapsed], updateSidebarWidthProperty, { immediate: true });

onMounted(() => {
  updateSidebarWidthProperty();
  
  if (window.history.state && window.history.state.editNameInline && 'id' in route.params && route.params.id) {
    const id = Number(route.params.id);
    const p = store.portfolios.find(ptf => ptf.id === id);
    if (p) {
      editingPortfolioId.value = id;
      editingName.value = p.name;
    }
  }
});

const isResizing = ref(false);
let activeMouseMoveHandler: ((e: MouseEvent) => void) | null = null;
let activeMouseUpHandler: (() => void) | null = null;

const startResize = (e: MouseEvent) => {
  e.preventDefault();
  isResizing.value = true;
  document.body.style.cursor = 'ew-resize';
  document.body.style.userSelect = 'none';

  activeMouseMoveHandler = (event: MouseEvent) => {
    if (!isResizing.value) return;
    const newWidth = event.clientX;
    store.setSidebarWidth(newWidth);
  };

  activeMouseUpHandler = () => {
    isResizing.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    if (activeMouseMoveHandler) window.removeEventListener('mousemove', activeMouseMoveHandler);
    if (activeMouseUpHandler) window.removeEventListener('mouseup', activeMouseUpHandler);
    activeMouseMoveHandler = null;
    activeMouseUpHandler = null;
  };

  window.addEventListener('mousemove', activeMouseMoveHandler);
  window.addEventListener('mouseup', activeMouseUpHandler);
};

const showProfileMenu = ref(false);
const toggleProfileMenu = () => {
  showProfileMenu.value = !showProfileMenu.value;
};
const closeProfileMenu = () => {
  showProfileMenu.value = false;
};

onMounted(() => {
  window.addEventListener('click', closeProfileMenu);
});
onBeforeUnmount(() => {
  window.removeEventListener('click', closeProfileMenu);
  if (activeMouseMoveHandler) window.removeEventListener('mousemove', activeMouseMoveHandler);
  if (activeMouseUpHandler) window.removeEventListener('mouseup', activeMouseUpHandler);
});
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: store.sidebarCollapsed, 'is-resizing': isResizing }">
    <div v-if="!store.sidebarCollapsed" class="resize-handle" @mousedown="startResize"></div>

    <div class="sidebar-logo">
      <div class="flex items-center gap-3 overflow-hidden" :class="{ 'justify-center w-full': store.sidebarCollapsed }">
        <div class="logo-icon">K</div>
        <div v-show="!store.sidebarCollapsed" class="logo-text">Kapital</div>
      </div>
      <button 
        @click="store.toggleSidebar" 
        class="btn-collapse" 
        :title="store.sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'"
      >
        <ChevronLeft v-if="!store.sidebarCollapsed" class="collapse-icon" />
        <ChevronRight v-else class="collapse-icon" />
      </button>
    </div>

    <nav class="sidebar-nav">
      <div v-show="!store.sidebarCollapsed" class="nav-section-title">Overview</div>
      <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }" title="Global View">
        <LayoutDashboard class="nav-icon" />
        <span v-show="!store.sidebarCollapsed">Global View</span>
      </router-link>

      <div v-if="!store.sidebarCollapsed" class="nav-section-title flex justify-between items-center">
        <span>Portfolios</span>
        <button 
          @click="handleDirectCreatePortfolio" 
          class="bg-transparent border-0 text-text-tertiary cursor-pointer flex items-center"
          title="Create Portfolio"
          :disabled="isSubmitting"
        >
          <PlusCircle class="w-4 h-4" />
        </button>
      </div>
      <div v-else class="nav-divider"></div>

      <div v-if="store.loading && !store.portfolios.length" class="p-4 text-center text-text-tertiary">
        <Loader class="nav-icon animate-spin mx-auto" />
      </div>

      <div v-else-if="!store.portfolios.length && !store.sidebarCollapsed" class="px-3 py-2 text-xs text-text-tertiary italic">
        No portfolios created yet.
      </div>

      <template v-else-if="store.portfolios.length">
      <TransitionGroup name="portfolio-list" tag="div" class="flex flex-col gap-1"
        @dragover="onContainerDragOver"
      >
          <div 
            v-for="p in store.portfolios" 
            :key="p.id"
            draggable="true"
            @dragstart="onDragStart($event, p.id)"
            @dragend="onDragEnd"
            class="transition-all duration-300"
            :class="[
              dragSrcId === p.id ? 'opacity-25 bg-bg-tertiary border border-dashed border-accent rounded-md' : ''
            ]"
          >
            <!-- Router Link (When not editing) -->
            <router-link
              v-if="editingPortfolioId !== p.id"
              :to="'/portfolio/' + p.id"
              draggable="false"
              class="nav-link relative group"
              :class="[
                { active: route.path === '/portfolio/' + p.id },
                dragSrcId === p.id ? 'pointer-events-none' : ''
              ]"
              :title="p.name"
            >
              <!-- Emoji / Folder Icon Picker -->
              <EmojiPicker
                :modelValue="p.emoji"
                :disabled="store.sidebarCollapsed"
                @update:modelValue="store.setPortfolioEmoji(p.id, $event)"
                :class="store.sidebarCollapsed ? 'mr-0' : 'mr-2'"
              />

              <!-- Name Display -->
              <div v-show="!store.sidebarCollapsed" class="flex-1 min-w-0">
                <span 
                  @dblclick.stop="startRename(p)" 
                  class="block truncate select-none cursor-pointer"
                >
                  {{ p.name }}
                </span>
              </div>
            </router-link>

            <!-- Edit Input Div (When editing) -->
            <div
              v-else
              class="nav-link relative group active flex items-center"
              :title="p.name"
            >
              <EmojiPicker
                :modelValue="p.emoji"
                :disabled="store.sidebarCollapsed"
                @update:modelValue="store.setPortfolioEmoji(p.id, $event)"
                :class="store.sidebarCollapsed ? 'mr-0' : 'mr-2'"
              />

              <!-- Name Input -->
              <div v-show="!store.sidebarCollapsed" class="flex-1 min-w-0">
                <input
                  ref="renameInput"
                  v-model="editingName"
                  class="bg-bg-tertiary text-text-primary border-0 outline-none ring-0 p-0 px-1.5 w-full rounded text-[0.925rem] font-medium leading-tight"
                  @keydown.enter="saveRename(p.id)"
                  @keydown.esc="cancelRename"
                  @blur="saveRename(p.id)"
                  @click.stop.prevent
                />
              </div>
            </div>
          </div>
        </TransitionGroup>
      </template>

      <!-- Separate entry for Unassigned Holdings fallback pool -->
      <router-link 
        v-if="store.hasUnassignedPositions"
        to="/portfolio/unassigned"
        class="nav-link mt-2 border border-dashed border-border-color rounded-md hover:bg-bg-tertiary transition-colors"
        :class="{ active: route.path === '/portfolio/unassigned' }"
        title="Unassigned Holdings"
      >
        <Folder class="nav-icon text-amber-500" />
        <span v-show="!store.sidebarCollapsed" class="truncate text-text-secondary">Unassigned Holdings</span>
      </router-link>

      <button 
        v-if="store.sidebarCollapsed"
        @click="handleDirectCreatePortfolio" 
        class="nav-link w-full border-none bg-transparent text-left flex justify-center py-1.5"
        title="Create Portfolio"
        :disabled="isSubmitting"
      >
        <PlusCircle class="nav-icon" style="color: var(--accent-color);" />
      </button>
    </nav>

    <div class="sidebar-profile relative">
      <button 
        @click.stop="toggleProfileMenu" 
        class="flex items-center w-full p-2 hover:bg-bg-tertiary rounded-md transition-colors text-left border-0 bg-transparent cursor-pointer"
        :class="store.sidebarCollapsed ? 'justify-center' : 'justify-between'"
      >
        <div :class="['flex items-center overflow-hidden', store.sidebarCollapsed ? 'justify-center' : 'gap-3']">
          <div class="avatar bg-accent text-white w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0">
            SE
          </div>
          <div v-show="!store.sidebarCollapsed" class="profile-info overflow-hidden">
            <span class="profile-name text-xs font-semibold text-text-primary block truncate">Senior Expert</span>
            <span class="profile-email text-[10px] text-text-secondary block truncate" :title="store.userEmail">{{ store.userEmail }}</span>
          </div>
        </div>
        <ChevronUp v-show="!store.sidebarCollapsed" class="w-4 h-4 text-text-secondary flex-shrink-0" />
      </button>

      <div 
        v-if="showProfileMenu" 
        class="absolute bottom-full mb-2 w-48 bg-bg-secondary border border-border-color rounded-md shadow-lg py-1 z-50 flex flex-col"
        :class="store.sidebarCollapsed ? 'left-2 translate-x-0' : 'left-1/2 -translate-x-1/2'"
        @click.stop
      >
        <router-link 
          to="/settings" 
          @click="showProfileMenu = false"
          class="flex items-center gap-2.5 px-4 py-2.5 text-xs text-text-primary hover:bg-bg-tertiary transition-colors w-full text-left"
        >
          <Settings class="w-4 h-4 text-text-secondary" />
          <span>Settings</span>
        </router-link>
        
        <div class="h-[1px] bg-border-color my-1"></div>
        
        <button 
          @click="handleLogout" 
          class="flex items-center gap-2.5 px-4 py-2.5 text-xs text-danger-color hover:bg-danger-light transition-colors w-full text-left border-0 bg-transparent cursor-pointer"
        >
          <LogOut class="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  </aside>
</template>
