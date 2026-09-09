<template>
  <div class="app">
    <header class="top-nav">
      <div class="nav-container">
        <div class="logo">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="subtitle">{{ t('nav.subtitle') }}</span>
        </div>
        <nav class="nav-tabs">
          <router-link to="/" :class="{ active: $route.path === '/' }">
            {{ t('nav.overview') }}
          </router-link>
          <router-link to="/inventory" :class="{ active: $route.path === '/inventory' }">
            {{ t('nav.inventory') }}
          </router-link>
          <router-link to="/orders" :class="{ active: $route.path === '/orders' }">
            {{ t('nav.orders') }}
          </router-link>
          <router-link to="/spending" :class="{ active: $route.path === '/spending' }">
            {{ t('nav.finance') }}
          </router-link>
          <router-link to="/demand" :class="{ active: $route.path === '/demand' }">
            {{ t('nav.demandForecast') }}
          </router-link>
          <router-link to="/restocking" :class="{ active: $route.path === '/restocking' }">
            {{ t('nav.restocking') }}
          </router-link>
          <router-link to="/reports" :class="{ active: $route.path === '/reports' }">
            Reports
          </router-link>
        </nav>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </header>
    <FilterBar />
    <main class="main-content">
      <router-view />
    </main>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* Warm neutral ramp */
  --gray-0: #ffffff;  --gray-10: #fcfcfb; --gray-20: #f9f9f7; --gray-40: #f3f3f0;
  --gray-60: #edece8; --gray-100: #e1e0d9; --gray-150: #d2d1c7; --gray-200: #c3c2b7;
  --gray-300: #a5a49a; --gray-400: #898781; --gray-500: #6d6b67; --gray-600: #52514e;
  --gray-700: #383835; --gray-800: #20201f; --gray-900: #0b0b0b;

  /* Surfaces */
  --page-bg: var(--gray-20);
  --surface: var(--gray-0);          /* cards, tables, modals, inputs */
  --surface-subtle: var(--gray-10);  /* table hover, secondary panels */
  --surface-muted: var(--gray-40);   /* nav hover, chips, progress track */

  /* Text */
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-600);
  --text-muted: var(--gray-400);
  --text-on-fill: var(--gray-0);

  /* Borders (alpha so they sit on any surface) */
  --border: rgba(11, 11, 11, 0.10);
  --border-strong: rgba(11, 11, 11, 0.18);

  /* Brand (clay) — primary buttons, active nav, selected states, primary chart series */
  --brand: #d97757;
  --brand-emphasized: #c6613f;  /* default fill; --brand is hover */
  --brand-bg: #f7d8cb;
  --brand-border: #f09978;

  /* Accent (blue) — INFORMATIONAL only: "info" badges, stable trend, links */
  --accent: #2a78d6;
  --accent-text: #184f95;
  --accent-bg: #cde2fb;
  --accent-border: #86b6ef;

  /* Status */
  --success: #009300;  --success-text: #006300; --success-bg: #caeac7; --success-border: #73cb6d;
  --warning: #fab219;  --warning-text: #734500; --warning-bg: #f9dca4; --warning-border: #eda100;
  --danger:  #d03b3b;  --danger-text:  #8e2626; --danger-bg:  #fad6d6; --danger-border:  #f09595;

  /* Type */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --font-display: ui-serif, "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  /* Shape + elevation */
  --radius-sm: 6px; --radius: 8px; --radius-lg: 12px; --radius-pill: 999px;
  --shadow-sm: 0 1px 2px 0 rgba(11,11,11,0.06), 0 2px 8px 0 rgba(11,11,11,0.04);
  --shadow-md: 0 2px 4px 0 rgba(11,11,11,0.07), 0 6px 16px 0 rgba(11,11,11,0.06);
  --shadow-lg: 0 4px 8px 0 rgba(11,11,11,0.08), 0 12px 28px -2px rgba(11,11,11,0.10);
  --focus-ring: 0 0 0 1px var(--surface), 0 0 0 3px var(--brand-border);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  background: var(--page-bg);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-nav {
  background: var(--page-bg);
  border-bottom: 1px solid var(--border);
  box-shadow: none;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 60px;
}

.nav-container > .nav-tabs {
  margin-left: auto;
  margin-right: 1rem;
}

.nav-container > .language-switcher {
  margin-right: 1rem;
}

/* The header holds a logo, seven tabs, a language switcher and a profile menu; below ~1500px
   the subtitle is the first thing to give way so nothing wraps onto a second line. */
@media (max-width: 1500px) {
  .subtitle {
    display: none;
  }
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.logo h1 {
  white-space: nowrap;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.subtitle {
  white-space: nowrap;
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-weight: 400;
}

.nav-tabs {
  display: flex;
  gap: 0.25rem;
}

.nav-tabs a {
  white-space: nowrap;
  padding: 0.5rem 0.75rem;
  color: var(--text-secondary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
  position: relative;
}

.nav-tabs a:hover {
  color: var(--text-primary);
  background: var(--surface-muted);
}

.nav-tabs a.active {
  color: var(--text-primary);
  background: transparent;
}

.nav-tabs a.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0.75rem;
  right: 0.75rem;
  height: 2px;
  background: var(--brand-emphasized);
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
  letter-spacing: -0.01em;
  line-height: 1.2;
}

.page-header p {
  color: var(--text-secondary);
  font-size: 0.9375rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--surface);
  padding: 1.25rem 1.375rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.stat-card.warning .stat-value {
  color: var(--warning-text);
}

.stat-card.success .stat-value {
  color: var(--success-text);
}

.stat-card.danger .stat-value {
  color: var(--danger-text);
}

.stat-card.info .stat-value {
  color: var(--accent-text);
}

.card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: transparent;
  border-top: none;
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: 0.625rem 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 0.75rem;
  letter-spacing: 0;
}

td {
  padding: 0.625rem 0.75rem;
  border-top: 1px solid var(--border);
  color: var(--text-primary);
  font-size: 0.875rem;
}

td.numeric,
th.numeric {
  font-variant-numeric: tabular-nums;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--surface-subtle);
}

.badge {
  display: inline-block;
  padding: 0.125rem 0.625rem;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0;
  border: 1px solid transparent;
}

.badge.success,
.badge.increasing {
  background: var(--success-bg);
  color: var(--success-text);
  border-color: var(--success-border);
}

.badge.warning,
.badge.medium {
  background: var(--warning-bg);
  color: var(--warning-text);
  border-color: var(--warning-border);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--danger-bg);
  color: var(--danger-text);
  border-color: var(--danger-border);
}

.badge.info,
.badge.low,
.badge.stable {
  background: var(--accent-bg);
  color: var(--accent-text);
  border-color: var(--accent-border);
}

.badge.neutral {
  background: var(--surface-muted);
  color: var(--text-secondary);
  border-color: var(--border);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
  font-size: 0.938rem;
}

.error {
  background: var(--danger-bg);
  border: 1px solid var(--danger-border);
  color: var(--danger-text);
  padding: 1rem;
  border-radius: var(--radius);
  margin: 1rem 0;
  font-size: 0.938rem;
}

/* Global button classes shared by views and modals */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.875rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.btn:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.btn-primary {
  background: var(--brand-emphasized);
  color: var(--text-on-fill);
}

.btn-primary:hover {
  background: var(--brand);
}

.btn-secondary {
  background: var(--surface);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.btn-secondary:hover {
  background: var(--surface-muted);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: transparent;
}

.btn-ghost:hover {
  background: var(--surface-muted);
  color: var(--text-primary);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Global form controls */
select,
input[type="text"],
input[type="number"],
textarea {
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: inherit;
  font-size: inherit;
  padding: 0.4rem 0.625rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

select:hover,
input[type="text"]:hover,
input[type="number"]:hover,
textarea:hover {
  border-color: var(--gray-300);
}

select:focus-visible,
input[type="text"]:focus-visible,
input[type="number"]:focus-visible,
textarea:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
  border-color: var(--brand-border);
}

input[type="range"],
input[type="checkbox"] {
  accent-color: var(--brand-emphasized);
}
</style>
