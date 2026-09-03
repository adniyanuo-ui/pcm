<template>
  <div class="button_group">
    <el-button type="primary" round disabled>挂号</el-button>
    <el-button type="primary" round @click.native="to_question">预问诊</el-button>
    <el-button type="primary" round disabled>诊疗结果</el-button>
  </div>
</template>

<script>
import router from "@/router";


export default {
  name: "welcome",
  components: {},
  data() {
    return {};
  },
  methods: {
    to_question() {
      router.push({path: "/question"})
    },
    check_login() {
      if (!localStorage.getItem("token")) {
        router.push({path: "/login"})
      }
    },
  },
  mounted() {
    this.check_login()
  }
};
</script>

<style scoped>
.button_group {
  margin: 10px;
  text-align: center;
  display: flex;
}
</style>
