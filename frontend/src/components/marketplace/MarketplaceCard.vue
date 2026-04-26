<template>
  <el-card class="marketplace-card" :class="{ disabled: !item.enabled }" shadow="hover">
    <div class="card-header">
      <h3 class="item-name">{{ item.name }}</h3>
      <el-tag size="small" :type="typeTagType">{{ typeLabel }}</el-tag>
    </div>
    <div class="card-content">
      <p class="item-description">{{ item.description || '暂无描述' }}</p>
      <div v-if="item.tags.length" class="tag-list">
        <el-tag v-for="tag in item.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
      </div>
    </div>
    <div class="card-footer">
      <div class="meta">
        <span>版本 {{ item.version }}</span>
        <span>{{ item.source_platform }}</span>
      </div>
      <div class="actions">
        <el-switch v-model="localEnabled" :loading="loading" :disabled="loading" @change="handleToggle" />
        <el-button type="danger" size="small" text :icon="Delete" title="删除" @click.stop="emit('delete', { id: item.id, item_type: item.item_type })" />
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import type { MarketplaceItem, MarketplaceTogglePayload, MarketplaceItemType } from '@/stores/marketplace'

const props = defineProps<{ item: MarketplaceItem; loading: boolean }>()

const emit = defineEmits<{
  (e: 'toggle', payload: MarketplaceTogglePayload): void
  (e: 'delete', payload: { id: number; item_type: MarketplaceItemType }): void
}>()

const localEnabled = ref(props.item.enabled)

const typeTagType = computed(() => {
  if (props.item.item_type === 'tool') return 'primary'
  if (props.item.item_type === 'skill') return 'success'
  return 'warning'
})

const typeLabel = computed(() => {
  if (props.item.item_type === 'tool') return 'Tool'
  if (props.item.item_type === 'skill') return 'Skill'
  return 'Agent'
})

watch(() => props.item.enabled, (enabled) => { localEnabled.value = enabled })
watch(() => props.loading, (loading) => { if (!loading) localEnabled.value = props.item.enabled })

function handleToggle(enabled: boolean) {
  emit('toggle', { id: props.item.id, item_type: props.item.item_type, enabled })
}
</script>

<style scoped>
.marketplace-card { transition: opacity 0.2s ease, transform 0.2s ease; }
.marketplace-card:hover { transform: translateY(-2px); }
.marketplace-card.disabled { opacity: 0.7; }
.card-header, .card-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-header { margin-bottom: 12px; }
.card-content { min-height: 108px; }
.item-name { margin: 0; font-size: 16px; font-weight: 600; color: #303133; }
.item-description { margin: 0 0 12px; font-size: 13px; line-height: 1.6; color: #606266; word-break: break-word; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.card-footer { margin-top: 16px; padding-top: 14px; border-top: 1px solid #ebeef5; }
.actions { display: flex; align-items: center; gap: 8px; }
.meta { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #909399; }
</style>
