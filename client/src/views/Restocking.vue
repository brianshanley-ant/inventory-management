<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="lastOrder" class="success-banner">
      <span>
        {{ t('restocking.orderPlaced', {
          orderNumber: lastOrder.order_number,
          date: formatDate(lastOrder.expected_delivery),
          days: lastOrder.lead_time_days
        }) }}
      </span>
      <router-link to="/orders" class="banner-link">{{ t('restocking.viewOrders') }}</router-link>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="stats-grid">
      <div class="stat-card info">
        <div class="stat-label">{{ t('restocking.budget') }}</div>
        <div class="stat-value">{{ formatMoney(budget) }}</div>
      </div>
      <div class="stat-card success">
        <div class="stat-label">{{ t('restocking.plannedSpend') }}</div>
        <div class="stat-value">{{ formatMoney(totalCost) }}</div>
      </div>
      <div class="stat-card warning">
        <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
        <div class="stat-value">{{ formatMoney(remainingBudget) }}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
      </div>
      <div class="budget-controls">
        <div class="budget-slider">
          <div class="budget-amount">{{ formatMoney(budget) }}</div>
          <input
            type="range"
            min="0"
            max="50000"
            step="500"
            v-model.number="budget"
            :aria-label="t('restocking.budget')"
            class="range-input"
          />
        </div>
        <label class="warehouse-field">
          <span class="field-label">{{ t('restocking.destinationWarehouse') }}</span>
          <select v-model="destinationWarehouse" class="warehouse-select">
            <option v-for="name in warehouses" :key="name" :value="name">
              {{ translateWarehouse(name) }}
            </option>
          </select>
        </label>
      </div>
    </div>

    <div v-if="initialLoading" class="loading">{{ t('common.loading') }}</div>

    <template v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendations.length }})</h3>
        </div>
        <p v-if="recommendations.length === 0 && !loading" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </p>
        <div v-else :class="['table-container', { 'is-refreshing': loading }]">
          <table>
            <thead>
              <tr>
                <th v-for="col in columns" :key="col">{{ t(`restocking.table.${col}`) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in recommendations" :key="row.sku">
                <td><strong>{{ row.sku }}</strong></td>
                <td>{{ translateProductName(row.name) }}</td>
                <td>{{ translateCategory(row.category) }}</td>
                <td>{{ row.current_demand.toLocaleString() }}</td>
                <td>{{ row.forecasted_demand.toLocaleString() }}</td>
                <td>{{ row.gap.toLocaleString() }}</td>
                <td>{{ formatMoney(row.unit_cost) }}</td>
                <td>{{ row.recommended_quantity.toLocaleString() }}</td>
                <td><strong>{{ formatMoney(row.line_total) }}</strong></td>
                <td>{{ t('restocking.leadTimeDays', { days: row.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="skipped.length" class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">{{ t('restocking.skippedItems') }} ({{ skipped.length }})</h3>
            <p class="card-subtitle">{{ t('restocking.skippedHint') }}</p>
          </div>
        </div>
        <div :class="['table-container', { 'is-refreshing': loading }]">
          <table>
            <thead>
              <tr>
                <th v-for="col in columns" :key="col">{{ t(`restocking.table.${col}`) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in skipped" :key="row.sku" class="row-skipped">
                <td><strong>{{ row.sku }}</strong></td>
                <td>{{ translateProductName(row.name) }}</td>
                <td>{{ translateCategory(row.category) }}</td>
                <td>{{ row.current_demand.toLocaleString() }}</td>
                <td>{{ row.forecasted_demand.toLocaleString() }}</td>
                <td>{{ row.gap.toLocaleString() }}</td>
                <td>{{ formatMoney(row.unit_cost) }}</td>
                <td>
                  {{ row.recommended_quantity.toLocaleString() }}
                  <span class="badge warning">{{ t('restocking.overBudget') }}</span>
                </td>
                <td>{{ formatMoney(row.line_total) }}</td>
                <td>{{ t('restocking.leadTimeDays', { days: row.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div class="summary-bar">
      <div class="summary-text">
        <span class="summary-total">
          {{ t('restocking.total') }}: <strong>{{ formatMoney(totalCost) }}</strong>
          {{ t('restocking.of') }} {{ formatMoney(budget) }}
        </span>
        <span class="summary-remaining">
          {{ t('restocking.remainingBudget') }}: {{ formatMoney(remainingBudget) }}
        </span>
      </div>
      <button
        class="place-order-btn"
        :disabled="placing || loading || recommendations.length === 0"
        @click="placeOrder"
      >
        {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const WAREHOUSES = ['San Francisco', 'London', 'Tokyo']
const COLUMNS = ['sku', 'item', 'category', 'currentDemand', 'forecastedDemand', 'gap', 'unitCost', 'quantity', 'lineTotal', 'leadTime']
const DEBOUNCE_MS = 250

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateWarehouse, translateProductName } = useI18n()
    const { selectedLocation } = useFilters()

    const budget = ref(10000)
    const destinationWarehouse = ref(
      selectedLocation.value !== 'all' ? selectedLocation.value : 'San Francisco'
    )
    const warehouses = WAREHOUSES
    const columns = COLUMNS

    const recommendations = ref([])
    const skipped = ref([])
    const totalCost = ref(0)
    const remainingBudget = ref(budget.value)

    const loading = ref(false)
    const initialLoading = ref(true)
    const placing = ref(false)
    const error = ref(null)
    const lastOrder = ref(null)

    let requestCounter = 0
    let debounceTimer = null

    const formatMoney = (value) => formatCurrencyWithDecimals(value || 0, currentCurrency.value, 2)

    // Same mapping the Dashboard uses so category names localize consistently

    const CATEGORY_KEYS = {

      'Circuit Boards': 'circuitBoards',

      'Sensors': 'sensors',

      'Actuators': 'actuators',

      'Controllers': 'controllers',

      'Power Supplies': 'powerSupplies'

    }

    const translateCategory = (category) => {

      const key = CATEGORY_KEYS[category]

      return key ? t(`categories.${key}`) : category

    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return ''
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const loadRecommendations = async () => {
      const requestId = ++requestCounter
      loading.value = true
      try {
        const data = await api.getRestockRecommendations(budget.value)
        if (requestId !== requestCounter) return
        recommendations.value = data.recommendations || []
        skipped.value = data.skipped || []
        totalCost.value = data.total_cost || 0
        remainingBudget.value = data.remaining_budget ?? budget.value
        error.value = null
      } catch (err) {
        if (requestId !== requestCounter) return
        const detail = err.response?.data?.detail
        error.value = detail ? `${t('common.error')}: ${detail}` : `${t('common.error')}: ${err.message}`
        console.error('Failed to load restock recommendations:', err)
      } finally {
        if (requestId === requestCounter) {
          loading.value = false
          initialLoading.value = false
        }
      }
    }

    const placeOrder = async () => {
      if (placing.value || recommendations.value.length === 0) return
      placing.value = true
      try {
        const order = await api.createRestockOrder({
          budget: budget.value,
          warehouse: destinationWarehouse.value,
          items: recommendations.value.map(r => ({ sku: r.sku, quantity: r.recommended_quantity }))
        })
        lastOrder.value = order
        error.value = null
      } catch (err) {
        const detail = err.response?.data?.detail
        error.value = detail
          ? `${t('restocking.orderFailed')}: ${detail}`
          : `${t('restocking.orderFailed')}: ${err.message}`
        console.error('Failed to place restock order:', err)
      } finally {
        placing.value = false
      }
    }

    watch(budget, () => {
      // Mark as loading immediately so Place Order cannot submit the previous
      // recommendation set against the new budget during the debounce window
      loading.value = true
      lastOrder.value = null
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
    })

    watch(selectedLocation, (value) => {
      if (value !== 'all') destinationWarehouse.value = value
    })

    onMounted(loadRecommendations)

    onBeforeUnmount(() => {
      clearTimeout(debounceTimer)
    })

    return {
      t,
      translateWarehouse,
      translateProductName,
      budget,
      destinationWarehouse,
      warehouses,
      columns,
      recommendations,
      skipped,
      totalCost,
      remainingBudget,
      loading,
      initialLoading,
      placing,
      error,
      lastOrder,
      formatMoney,
      translateCategory,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.success-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  font-size: 0.938rem;
}

.banner-link {
  color: #065f46;
  font-weight: 600;
  text-decoration: underline;
  white-space: nowrap;
}

.budget-controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 2rem;
  align-items: end;
}

.budget-slider {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.budget-amount {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.range-input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

/* Vendor pseudo-elements must stay in separate rules: an unrecognized
   selector in a comma list invalidates the whole rule. */
.range-input::-webkit-slider-runnable-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
}

.range-input::-moz-range-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  margin-top: -6px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.3);
  cursor: pointer;
}

.range-input::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #3b82f6;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.3);
  cursor: pointer;
}

.range-input:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}

.range-input:focus-visible::-moz-range-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}

.warehouse-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #64748b;
}

.warehouse-select {
  padding: 0.4rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.813rem;
  color: #0f172a;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  min-width: 160px;
}

.warehouse-select:hover {
  border-color: #94a3b8;
}

.warehouse-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.card-subtitle {
  margin-top: 0.25rem;
  font-size: 0.813rem;
  color: #64748b;
}

.empty-state {
  padding: 2rem 0;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

.table-container {
  transition: opacity 0.15s ease;
}

.table-container.is-refreshing {
  opacity: 0.6;
}

.row-skipped {
  opacity: 0.55;
}

.row-skipped .badge {
  margin-left: 0.5rem;
}

.summary-bar {
  position: sticky;
  bottom: 0;
  background: white;
  border-top: 1px solid #e2e8f0;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  z-index: 5;
}

.summary-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.summary-total {
  font-size: 0.938rem;
  color: #0f172a;
}

.summary-remaining {
  font-size: 0.813rem;
  color: #64748b;
}

.place-order-btn {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  background: #3b82f6;
  color: white;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .budget-controls {
    grid-template-columns: 1fr;
  }
}
</style>
