import { createRouter, createWebHistory } from 'vue-router';
import { routes } from 'vue-router/auto-routes';
import { api } from '../services/api';

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const isAuth = api.isAuthenticated();

  if (to.meta.requiresAuth && !isAuth) {
    return { name: 'login' };
  } else if (to.meta.requiresGuest && isAuth) {
    return { name: 'dashboard' };
  }
});
