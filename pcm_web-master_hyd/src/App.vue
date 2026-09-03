<template>
	<div id="app">
		<el-container class="quiz-content">
			<el-header height="auto" style="border-bottom: 1px solid #cccccc;">
				<div style="display: flex;justify-content: space-between;align-items: center">
					<div style="margin: 0 auto">
						<h1 v-if="!show_logout" class="title">穿山甲系统</h1>
						<h1 v-else class="title">穿山甲系统({{ name }})</h1>
					</div>
					<div v-if="show_logout">
						<el-button type="text" style="margin-left: 20px" @click="logout">重新开始</el-button>
					</div>
				</div>
			</el-header>
			<el-main>
				<router-view/>
			</el-main>
		</el-container>
	</div>
</template>
<script>
import moment from 'moment';
import {on_get_question, on_submit} from "@/api/question";
import {on_add_patient} from "@/api/welcome";
import router from "@/router";

export default {
	name: "question",
	components: {},
	data() {
		return {
			show_logout: false,
			name: "",
		};
	},
	methods: {
		get_name() {
			if (localStorage.getItem("token")) {
				this.name = localStorage.getItem("name")
			}
			this.show_logout = !!this.name;
		},
		logout() {
			localStorage.removeItem("token")
			localStorage.removeItem("name")
			this.name = ""
			this.show_logout = false
			window.location.href = "/"
		}
	},
	mounted() {
		this.get_name()
	}
};
</script>
<style lang="less">
.quiz-content {
	/*box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);*/
	background-color: white;
	width: 80%;
	margin: 0 auto;
	padding: 10px;
}
</style>
