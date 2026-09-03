<template>
  <div>
    <el-container class="quiz-content">
      <el-main style="text-align: center">
        <div class="user-info">
          <el-form inline label-width="100px" :model="user" :rules="rules" ref="user">
            <el-form-item label="手机号:" prop="username">
              <el-input v-model="user.username" size="default"></el-input>
            </el-form-item>

            <br/>

            <el-form-item label="密码:" prop="password">
              <el-input v-model="user.password" size="default" type="password" show-password  style="width: 177.5px"></el-input>
            </el-form-item>
          </el-form>
        </div>
      </el-main>

      <el-footer style="margin: auto">
        <el-button type="primary" @click="on_submit">登陆</el-button>
        <el-button @click="to_register">注册</el-button>
      </el-footer>

    </el-container>
  </div>
</template>

<script>
import router from "@/router";
import {on_login} from "@/api/login";


export default {
  name: "login",
  components: {},
  data() {
    return {
      user: {
        "username": "",
        "password": "",
      },
    };
  },
  methods: {
    on_submit() {
      on_login(this.user).then(resp => {
        let name = resp.data.name
        localStorage.setItem("token", resp.data.token)
        localStorage.setItem("name", name)
        window.location.href = "/"
      })
    },
    to_register() {
      router.push({path: "/register"})
    },
    check_login() {
      if (localStorage.getItem("token")) {
        router.push({path: "/"})
      }
    },
  },
  mounted() {
    this.check_login()
  }
};
</script>

<style scoped>

</style>
