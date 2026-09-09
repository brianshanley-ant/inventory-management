<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && product" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">Product Details</h3>
            <button class="btn btn-ghost" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="product-header">
              <div class="product-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <rect x="8" y="12" width="32" height="28" rx="2" stroke="currentColor" stroke-width="2.5"/>
                  <path d="M16 8V16M32 8V16M8 20H40" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
                </svg>
              </div>
              <div class="product-title-section">
                <h4 class="product-name">{{ product.name }}</h4>
                <div class="product-sku">SKU: {{ product.sku }}</div>
              </div>
              <span class="stock-badge" :class="getStockBadgeClass(product.stockLevel)">
                {{ product.stockLevel }}
              </span>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">Category</div>
                <div class="info-value">{{ product.category }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Warehouse</div>
                <div class="info-value">{{ product.warehouse }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Units Ordered</div>
                <div class="info-value">{{ product.unitsOrdered }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Total Revenue</div>
                <div class="info-value">{{ currencySymbol }}{{ product.revenue.toLocaleString() }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Current Stock</div>
                <div class="info-value">{{ product.quantityOnHand }} units</div>
              </div>

              <div class="info-item">
                <div class="info-label">Reorder Point</div>
                <div class="info-value">{{ product.reorderPoint }} units</div>
              </div>

              <div class="info-item">
                <div class="info-label">First Order Date</div>
                <div class="info-value">{{ formatDate(product.firstOrderDate) }}</div>
              </div>

              <div class="info-item">
                <div class="info-label">Stock Status</div>
                <div class="info-value">
                  <span :class="['badge', getStockBadgeClass(product.stockLevel)]">
                    {{ product.stockLevel }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="close">Close</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n'

const { currentCurrency } = useI18n()

const currencySymbol = computed(() => {
  return currentCurrency.value === 'JPY' ? '¥' : '$'
})

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  product: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const getStockBadgeClass = (stockLevel) => {
  if (stockLevel === 'In Stock') return 'success'
  if (stockLevel === 'Low Stock') return 'warning'
  if (stockLevel === 'Out of Stock') return 'danger'
  return 'info'
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(11, 11, 11, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--border);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-family: var(--font-display);
  font-weight: 500;
  font-size: 1.25rem;
  color: var(--text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.product-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2rem;
}

.product-icon {
  width: 64px;
  height: 64px;
  background: var(--brand-emphasized);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-on-fill);
  flex-shrink: 0;
}

.product-title-section {
  flex: 1;
  min-width: 0;
}

.product-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.5rem 0;
}

.product-sku {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.stock-badge {
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-pill);
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid transparent;
  flex-shrink: 0;
}

.stock-badge.success {
  background: var(--success-bg);
  color: var(--success-text);
  border-color: var(--success-border);
}

.stock-badge.warning {
  background: var(--warning-bg);
  color: var(--warning-text);
  border-color: var(--warning-border);
}

.stock-badge.danger {
  background: var(--danger-bg);
  color: var(--danger-text);
  border-color: var(--danger-border);
}

.stock-badge.info {
  background: var(--accent-bg);
  color: var(--accent-text);
  border-color: var(--accent-border);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.info-value {
  font-size: 0.9375rem;
  color: var(--text-primary);
  font-weight: 500;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
