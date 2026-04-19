<template>
  <el-tag :type="enabled ? 'success' : 'info'" size="small" effect="plain">
    {{ enabled ? '启用' : '禁用' }}
  </el-tag>
</template>

<script setup lang="ts">
defineProps<{ enabled: boolean }>()
</script>
