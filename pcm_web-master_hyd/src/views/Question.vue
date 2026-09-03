<template>
	<div>
		<el-container class="quiz-content">
			<el-header height="0"></el-header>

			<el-main>
				<el-container style="box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);">
					<el-header class="header">

						<el-breadcrumb separator-class="el-icon-arrow-right">
							<el-breadcrumb-item v-for="parent in this.question.parent_titles" style="color: black">
								{{ parent.title_number }}&nbsp;&nbsp;
								{{ parent.title }}
							</el-breadcrumb-item>
						</el-breadcrumb>

						<el-button-group>
							<el-button size="mini" type="primary"
									   icon="el-icon-arrow-left"
									   :disabled="pre_disabled()"
									   @click="to_next(false)">
								上一题
							</el-button>
							<el-button size="mini" type="primary" @click="to_next(true)"
									   :disabled="next_disabled()">
								下一题
								<i class="el-icon-arrow-right el-icon--right"></i>
							</el-button>
						</el-button-group>

					</el-header>
					<el-main style="overflow: scroll;height: 70vh">
						<question-item :question="[question]" :answer="answer" :parent="null"></question-item>
					</el-main>
				</el-container>
			</el-main>

			<el-footer style="margin: auto" v-if="question.next_id === 0 && Object.values(this.answer).some(Boolean)">
				<el-button type="primary" @click="on_submit">提交</el-button>
			</el-footer>

		</el-container>

	</div>
</template>

<script>
import QuestionItem from '@/components/question_item.vue';
import {get_result, on_get_question, on_submit_answer} from "@/api/question";
import router from "@/router";

export default {
	name: "question",
	components: {
		QuestionItem,
	},
	data() {
		return {
			question: {},
			answer: {},
		};
	},
	methods: {
		pre_disabled() {
			// return false;
			let flag1 = "id" in this.question;
			// 有一个选了给了答案
			let flag2 = Object.values(this.answer).some(Boolean);
			// 有上一题
			let flag3 = this.question.pre_id;
			return !flag1 || !flag2 || !flag3
		},
		next_disabled() {
			// return false;
			let flag1 = "id" in this.question;
			// 有一个选了给了答案
			let flag2 = Object.values(this.answer).some(Boolean);
			// 有下一题
			let flag3 = this.question.next_id;

			return !flag1 || !flag2 || !flag3
		},
		async to_next(is_next, get_question = true) {
			await on_submit_answer({"answer": this.answer, "q_id": this.question.id})
			if (get_question) {
				let next_id = is_next ? this.question.next_id : this.question.pre_id
				await this.get_question(next_id)
			}
		},
		async get_question(did = 0) {
			on_get_question(did).then(resp => {
				this.question = resp.data
				this.answer = this.question.answer
			})
		},
		async on_submit() {
			await this.to_next(0, false)
			await router.push({path: "/result"})
		}
	},
	mounted() {
		this.get_question(0)
	}
};
</script>

<style scoped>
.header {
	height: 50px;
	border-bottom: 1px solid #cccccc;
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.quiz-content {
	/*box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);*/
	background-color: white;
	width: 80%;
	margin: 0 auto;
	padding: 10px;
}

/deep/ .el-breadcrumb__item:last-child .el-breadcrumb__inner, .el-breadcrumb__item:last-child .el-breadcrumb__inner a, .el-breadcrumb__item:last-child .el-breadcrumb__inner a:hover, .el-breadcrumb__item:last-child .el-breadcrumb__inner:hover {
	color: black;
	font-size: large;
}
</style>
