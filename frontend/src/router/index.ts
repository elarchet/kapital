import { createRouter, createWebHistory } from 'vue-router';
import { api } from '../services/api';
import LoginView from '../views/LoginView.vue';
import DashboardView from '../views/DashboardView.vue';
import PortfolioView from '../views/PortfolioView.vue';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresGuest: true }
  },
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true }
  },
  {
    path: '/portfolio/:id',
    name: 'portfolio',
    component: PortfolioView,
    meta: { requiresAuth: true }
  },
  // Catch-all
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  const isAuth = api.isAuthenticated();

  if (to.meta.requiresAuth && !isAuth) {
    next({ name: 'login' });
  } else if (to.meta.requiresGuest && isAuth) {
    next({ name: 'dashboard' });
  } else {
    next();
  }
});
