<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useKapitalStore } from '../store';
import { api } from '../services/api';
import { 
  LayoutDashboard, 
  LogOut, 
  PlusCircle, 
  Folder,
  Loader,
  ChevronLeft,
  ChevronRight
} from '@lucide/vue';
import { SIDEBAR_CONFIG } from '../config/sidebar';

const router = useRouter();
const route = useRoute();
const store = useKapitalStore();

const showCreateModal = ref(false);
const newPortfolioName = ref('');
const newPortfolioDesc = ref('');
const isSubmitting = ref(false);
const submitError = ref('');

const handleLogout = () => {
  api.logout();
  store.setAuthenticated(false);
  router.push('/login');
};

const handleCreatePortfolio = async () => {
  if (!newPortfolioName.value.trim()) return;
  isSubmitting.value = true;
  submitError.value = '';
  try {
    await store.createPortfolio(newPortfolioName.value, newPortfolioDesc.value);
    newPortfolioName.value = '';
    newPortfolioDesc.value = '';
    showCreateModal.value = false;
  } finally {
    isSubmitting.value = false;
  }
};

// Write custom property for global CSS width consumption
const updateSidebarWidthProperty = () => {
  const width = store.sidebarCollapsed 
    ? `${SIDEBAR_CONFIG.COLLAPSED_WIDTH}px` 
    : `${store.sidebarWidth}px`;
  document.documentElement.style.setProperty('--sidebar-width', width);
};

watch(() => [store.sidebarWidth, store.sidebarCollapsed], updateSidebarWidthProperty, { immediate: true });

onMounted(() => {
  updateSidebarWidthProperty();
});

const isResizing = ref(false);

const startResize = (e: MouseEvent) => {
  e.preventDefault();
  isResizing.value = true;
  document.body.style.cursor = 'ew-resize';
  document.body.style.userSelect = 'none';

  const handleMouseMove = (event: MouseEvent) => {
    if (!isResizing.value) return;
    const newWidth = event.clientX;
    store.setSidebarWidth(newWidth);
  };

  const handleMouseUp = () => {
    isResizing.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  };

  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', handleMouseUp);
};
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: store.sidebarCollapsed, 'is-resizing': isResizing }">
    <!-- Resize handle border, only enabled when expanded -->
    <div v-if="!store.sidebarCollapsed" class="resize-handle" @mousedown="startResize"></div>

    <div class="sidebar-logo">
      <div style="display: flex; align-items: center; gap: 0.75rem; overflow: hidden;">
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
      <!-- Section: Overview -->
      <div v-show="!store.sidebarCollapsed" class="nav-section-title">Overview</div>
      <router-link to="/" class="nav-link" :class="{ active: route.path === '/' }" title="Global View">
        <LayoutDashboard class="nav-icon" />
        <span v-show="!store.sidebarCollapsed">Global View</span>
      </router-link>

      <!-- Section: Portfolios -->
      <div v-if="!store.sidebarCollapsed" class="nav-section-title" style="display: flex; justify-content: space-between; align-items: center;">
        <span>Portfolios</span>
        <button 
          @click="showCreateModal = true" 
          style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center;"
          title="Create Portfolio"
        >
          <PlusCircle style="width: 16px; height: 16px;" />
        </button>
      </div>
      <div v-else class="nav-divider"></div>

      <div v-if="store.loading && !store.portfolios.length" style="padding: 1rem; text-align: center; color: var(--text-tertiary);">
        <Loader class="nav-icon" style="animation: spin 1.5s linear infinite; margin: 0 auto;" />
      </div>

      <div v-else-if="!store.portfolios.length && !store.sidebarCollapsed" style="padding: 0.5rem 0.75rem; font-size: 0.8rem; color: var(--text-tertiary); font-style: italic;">
        No portfolios created yet.
      </div>

      <template v-else-if="store.portfolios.length">
        <router-link 
          v-for="p in store.portfolios" 
          :key="p.id" 
          :to="'/portfolio/' + p.id" 
          class="nav-link"
          :class="{ active: route.path === '/portfolio/' + p.id }"
          :title="p.name"
        >
          <Folder class="nav-icon" />
          <span v-show="!store.sidebarCollapsed" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ p.name }}</span>
        </router-link>
      </template>

      <!-- Collapsed Add Portfolio Action -->
      <button 
        v-if="store.sidebarCollapsed"
        @click="showCreateModal = true" 
        class="nav-link"
        title="Create Portfolio"
        style="width: 100%; border: none; background: none; text-align: left; display: flex; justify-content: center; padding: 0.75rem 0;"
      >
        <PlusCircle class="nav-icon" style="color: var(--accent-color);" />
      </button>
    </nav>

    <div class="sidebar-profile">
      <div v-show="!store.sidebarCollapsed" class="profile-info">
        <span class="profile-name">Senior Expert</span>
        <span class="profile-email" :title="store.userEmail">{{ store.userEmail }}</span>
      </div>
      <button @click="handleLogout" class="btn-logout" title="Log Out">
        <LogOut style="width: 18px; height: 18px;" />
      </button>
    </div>

    <!-- Create Portfolio Modal -->
    <div v-if="showCreateModal" class="modal-overlay">
      <div class="modal-card" style="max-width: 400px;">
        <div class="modal-header">
          <h3 class="table-title">New Portfolio</h3>
          <button @click="showCreateModal = false" style="background: none; border: none; cursor: pointer; font-size: 1.25rem;">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="submitError" class="login-error" style="margin-bottom: 1rem;">
            {{ submitError }}
          </div>
          <div class="form-group">
            <label for="portfolioName">Name</label>
            <input 
              v-model="newPortfolioName" 
              type="text" 
              id="portfolioName" 
              class="form-control" 
              placeholder="e.g. Pension Fund"
              required 
            />
          </div>
          <div class="form-group">
            <label for="portfolioDesc">Description</label>
            <textarea 
              v-model="newPortfolioDesc" 
              id="portfolioDesc" 
              class="form-control" 
              placeholder="Brief strategy outline"
              rows="3"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="btn btn-sm">Cancel</button>
          <button @click="handleCreatePortfolio" class="btn btn-sm btn-primary" :disabled="isSubmitting || !newPortfolioName.trim()">
            <span v-if="isSubmitting">Creating...</span>
            <span v-else>Create Portfolio</span>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
