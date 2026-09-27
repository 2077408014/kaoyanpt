<template>
  <div class="page">
    <el-page-header @back="router.back()" class="back">
      <template #content>
        <span class="title">学生学习详情</span>
      </template>
    </el-page-header>
    <OrgStudentPanel :student-id="studentId" :api="teacherApi" />
  </div>
</template>

<script setup>
import OrgStudentPanel from '../../components/OrgStudentPanel.vue';
import { teacherApi } from '../../api/organization';import { useRoute, useRouter } from "vue-router";
const route = useRoute();
const router = useRouter();
const studentId = Number(route.params.studentId);
</script>

<style scoped>
.page { padding: 24px; }
.back { margin-bottom: 16px; }
.title { font-weight: 600; }
</style>
