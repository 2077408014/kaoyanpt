<template>
  <router-view />
  <ForceChangePassword />
</template>

<script setup lang="ts">
import ForceChangePassword from './components/ForceChangePassword.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}
</style>
