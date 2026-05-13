<script setup lang="ts">
export interface WorkspaceTabItem {
  id: 'generate' | 'history' | 'admin'
  label: string
  badge?: string
}

defineProps<{
  tabs: WorkspaceTabItem[]
  ariaLabel?: string
}>()

const model = defineModel<WorkspaceTabItem['id']>({ required: true })
</script>

<template>
  <nav class="workspace-tabs" :aria-label="ariaLabel">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      :class="['workspace-tabs__item', { 'workspace-tabs__item--active': model === tab.id }]"
      :aria-current="model === tab.id ? 'page' : undefined"
      @click="model = tab.id"
    >
      <span>{{ tab.label }}</span>
      <span v-if="tab.badge" class="workspace-tabs__badge">{{ tab.badge }}</span>
    </button>
  </nav>
</template>

<style scoped>
.workspace-tabs {
  position: sticky;
  top: 0.75rem;
  z-index: 15;
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  gap: 0.25rem;
  padding: 0.25rem;
  border: 1px solid var(--line-soft);
  border-radius: 0.55rem;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(14px);
  overflow-x: auto;
}

.workspace-tabs__item {
  display: inline-flex;
  min-height: 2.55rem;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.9rem;
  border: 0;
  border-radius: 0.4rem;
  background: transparent;
  color: var(--ink-muted);
  font: inherit;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}

.workspace-tabs__item:hover {
  color: var(--ink-strong);
  background: rgba(15, 23, 42, 0.05);
}

.workspace-tabs__item--active {
  color: #fff;
  background: var(--ink-strong);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.workspace-tabs__badge {
  min-width: 1.45rem;
  padding: 0.1rem 0.4rem;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.12);
  color: var(--accent-blue);
  font-size: 0.75rem;
  line-height: 1.4;
  text-align: center;
}

.workspace-tabs__item--active .workspace-tabs__badge {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

@media (max-width: 720px) {
  .workspace-tabs {
    top: 0.5rem;
    width: 100%;
  }
}
</style>
