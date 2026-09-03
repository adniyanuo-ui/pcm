<template>
	<div class="test-result">
		<h1 style="white-space: pre">您的测评结果：{{ result }}</h1>
	</div>


</template>
<script>
import {get_result} from "@/api/question";

export default {
	name: "Result",
	data() {
		return {
			result: "" // 这里可以修改为实际的测试结果
		};
	},
	methods: {
		on_get_result() {
			get_result().then(resp => {
				this.result = resp.data
				// this.$message({
				// 	showClose: true,
				// 	message: msg,
				// 	type: 'warning',
				// 	duration: 0,
				// });
			})
		}
	},
	mounted() {
		this.on_get_result()
	}
};
</script>

<style scoped>
.test-result {
	text-align: center;
	margin-top: 50px;
}

h1 {
	font-size: 24px;
	color: #333;
}

p {
	font-size: 18px;
	color: #5cb85c; /* 浅绿色 */
}
</style>