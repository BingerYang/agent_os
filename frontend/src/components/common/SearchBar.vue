<template>
  <el-input
    v-model="keyword"
    :placeholder="placeholder"
    clearable
    :prefix-icon="Search"
    style="width: 240px"
    @input="onInput"
    @clear="emit('search', '')"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  placeholder?: string
  modelValue?: string
}>(), { placeholder: '搜索关键词', modelValue: '' })

const emit = defineEmits<{
  (e: 'search', value: string): void
  (e: 'update:modelValue', value: string): void
}>()

const keyword = ref(props.modelValue)

watch(() => props.modelValue, v => { keyword.value = v })

function onInput(val: string) {
  emit('update:modelValue', val)
  emit('search', val)
}
</script>
