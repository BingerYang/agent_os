<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background:#001529; overflow:hidden">
      <div style="color:white;padding:16px 20px;font-size:18px;font-weight:bold;border-bottom:1px solid #ffffff1a">
        Agent OS
      </div>
      <el-menu
        :default-active="route.path"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
        @select="(path: string) => router.push(path)"
      >
        <el-menu-item index="/workflow">
          <el-icon><Connection /></el-icon><span>Agent 工作流</span>
        </el-menu-item>
        <el-menu-item index="/mcp">
          <el-icon><Grid /></el-icon><span>插件广场</span>
        </el-menu-item>
        <el-menu-item index="/skills">
          <el-icon><Cpu /></el-icon><span>Skill 管理</span>
        </el-menu-item>
        <el-menu-item index="/pipelines">
          <el-icon><Bell /></el-icon><span>检测规则</span>
        </el-menu-item>
        <el-menu-item index="/agents">
          <el-icon><Avatar /></el-icon><span>Agent 管理</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Setting /></el-icon><span>模型配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header style="background:white;display:flex;align-items:center;padding:0 20px;box-shadow:0 1px 4px rgba(0,21,41,.08);z-index:10">
        <span style="font-size:16px;font-weight:500">{{ route.meta.title as string }}</span>
      </el-header>
      <el-main style="background:#f0f2f5;padding:20px;overflow:auto">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Connection, Grid, Cpu, Bell, Avatar, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
</script>
