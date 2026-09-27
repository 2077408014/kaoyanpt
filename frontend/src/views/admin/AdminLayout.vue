<template>
  <RoleLayout title="超级管理员" :items="menuItems" />
</template>

<script setup>
import RoleLayout from '../../components/RoleLayout.vue';import { OfficeBuilding, User } from "@element-plus/icons-vue";
const menuItems = [
  { index: "/admin/institutions", label: "机构管理", icon: OfficeBuilding },
  { index: "/admin/users", label: "账号管理", icon: User }
];
</script>
