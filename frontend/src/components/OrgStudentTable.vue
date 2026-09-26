<template>
  <el-table :data="students" v-loading="loading" stripe border>
    <el-table-column prop="username" label="学生" min-width="120" />
    <el-table-column prop="email" label="邮箱" min-width="180" />
    <el-table-column label="状态" width="90">
      <template #default="{ row }">
        <el-tag :type="row.status === 'suspended' ? 'danger' : 'success'" effect="plain">
          {{ row.status === 'suspended' ? '已暂停' : '正常' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="study_time_7d" label="近7天学习(分钟)" min-width="150" sortable />
    <el-table-column prop="words_7d" label="近7天单词" min-width="120" sortable />
    <el-table-column prop="questions_7d" label="近7天做题" min-width="120" sortable />
    <el-table-column prop="total_mistakes" label="累计错题" min-width="100" sortable />
    <el-table-column label="监督异常" min-width="100" sortable :sort-by="'supervision_abnormal'">
      <template #default="{ row }">
        <el-tag :type="row.supervision_abnormal > 0 ? 'danger' : 'success'" effect="plain">
          {{ row.supervision_abnormal }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" :width="removable ? 280 : 100" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" @click="$emit('view', row)">查看详情</el-button>
        <template v-if="removable">
          <el-button
            v-if="row.status !== 'suspended'"
            link
            type="warning"
            @click="$emit('suspend', row)"
          >暂停</el-button>
          <el-button
            v-else
            link
            type="success"
            @click="$emit('restore', row)"
          >恢复</el-button>
          <el-button link type="danger" @click="$emit('remove', row)">移出班级</el-button>
        </template>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { StudentSummary } from '../api/organization'

defineProps<{
  students: StudentSummary[]
  loading: boolean
  removable?: boolean
}>()

defineEmits<{
  (e: 'view', student: StudentSummary): void
  (e: 'remove', student: StudentSummary): void
  (e: 'suspend', student: StudentSummary): void
  (e: 'restore', student: StudentSummary): void
}>()
</script>
