<template>
  <div>
    <el-container class="quiz-content">
      <el-main>
        <!--            <h2 style="text-align: center">穿山甲精神健康测试题</h2>-->
        <!--            <h2>答题说明：</h2>-->
        <!--            <div>-->
        <!--              1、请测试者根据个人情况给出真实答案，个人对测试结果负责。-->
        <!--              <br/>-->
        <!--              2、本测试各题目可多选或单选，请测试者单击括号选择题目，但不得空题。-->
        <!--              <br/>-->
        <!--              3、测试题中的“最近”指的是最近三个月左右。-->
        <!--            </div>-->
        <h2>患者基本信息</h2>
        <div class="user-info">
          <el-form inline label-width="100px" :model="user" :rules="rules" ref="user">
            <el-form-item label="手机号:" prop="phone">
              <el-input v-model="user.phone" size="default"></el-input>
            </el-form-item>

            <el-form-item label="密码:" prop="password">
              <el-input type="password" show-password v-model="user.password" size="default" style="width: 177.5px"></el-input>
            </el-form-item>

            <br/>

            <el-form-item label="姓名:" prop="name">
              <el-input v-model="user.name" size="default"></el-input>
            </el-form-item>

            <el-form-item label="性别:" prop="sex">
              <el-select v-model="user.sex" size="default" style="width: 178px">
                <el-option label="男" value="男"/>
                <el-option label="女" value="女"/>
              </el-select>
            </el-form-item>

            <br/>

            <el-form-item label="身高(cm):" prop="height">
              <el-input v-model="user.height" size="default"></el-input>
            </el-form-item>

            <el-form-item label="体重(kg):" prop="weight">
              <el-input v-model="user.weight" size="default"></el-input>
            </el-form-item>

            <br/>

            <el-form-item label="年龄:" prop="age">
              <el-input v-model.number="user.age" size="default"></el-input>
            </el-form-item>

            <el-form-item label="婚姻状况:" prop="marital_status">
              <el-select v-model="user.marital_status" size="default" style="width: 178px">
                <el-option label="未婚" value="未婚"/>
                <el-option label="已婚" value="已婚"/>
                <el-option label="离异" value="离异"/>
                <el-option label="丧偶" value="丧偶"/>
              </el-select>
            </el-form-item>

            <br/>

            <el-form-item label="职业:">
              <el-input v-model="user.job" size="default"></el-input>
            </el-form-item>

            <el-form-item label="长期居住地:">
              <el-input v-model="user.origin" size="default"></el-input>
            </el-form-item>
          </el-form>
        </div>
      </el-main>

      <el-footer style="margin: auto">
        <el-button type="primary" @click="on_submit">提交</el-button>
      </el-footer>

    </el-container>
  </div>
</template>

<script>
import {on_add_patient} from "@/api/welcome";
import router from "@/router";


export default {
  name: "register",
  components: {},
  data() {
    return {
      user: {
        "name": "",
        "sex": "",
        "age": "",
        "height": "",
        "weight": "",
        "phone": "",
        "password": "",
        "marital_status": "",
        "job": "",
        "origin": "",
      },
      rules: {
        name: [
          {required: true, message: '请输入姓名', trigger: 'blur'},
          {min: 2, max: 10, message: '长度在 2 到 10 个字符', trigger: 'blur'}
        ],
        sex: [
          {required: true, message: '请选择性别', trigger: 'blur'}
        ],
        age: [
          {required: true, message: '年龄不能为空', trigger: 'blur'},
          {type: 'number', message: '年龄必须为数字值', trigger: 'blur'},
          {type: 'number', min: 10, max: 100, message: '年龄在 10 到 100 之间', trigger: 'blur'}
        ],
        height: [
          {required: true, message: '身高不能为空', trigger: 'blur'},
        ],
        weight: [
          {required: true, message: '体重不能为空', trigger: 'blur'},
        ],
        phone: [
          {required: true, message: '手机号不能为空', trigger: 'blur'},
        ],
        password: [
          {required: true, message: '密码不能为空', trigger: 'blur'},
        ],
        marital_status: [
          {required: true, message: '请选择婚姻状况', trigger: 'blur'}
        ],
      },
    };
  },
  methods: {
    on_submit() {
      this.$refs.user.validate(valid => {
        if (valid) {
          on_add_patient(this.user).then(resp => {
            let name = resp.data.name
            localStorage.setItem("token", resp.data.token)
            localStorage.setItem("name", name)
            window.location.href = "/"
          })
        }
      })
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
