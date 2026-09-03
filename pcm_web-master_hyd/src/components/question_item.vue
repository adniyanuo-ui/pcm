<template>
	<div>
		<div v-for="one_question in question" :style="get_display_style(one_question)" :class="get_class(one_question)">
			<div v-if="one_question.mode === -1" class="el-checkbox__label el-checkbox"
				 :style="get_color_style(one_question)">
				{{ get_title(one_question) }}
			</div>

			<!-- 多选题（mode === 3） -->
			<div v-if="one_question.mode === 3">
				<el-checkbox :label="one_question.id" v-model="answer[`${one_question.id}`]"
							 :style="get_color_style(one_question)" class="custom-checkbox"
							 @change="handleChange(one_question)"
				>
					{{ get_title(one_question) }}
				</el-checkbox>
			</div>

			<!-- 文本输入框 -->
			<div v-if="one_question.mode === 2 || one_question.mode === 4" class="child-title">
				<el-form label-width="80px" size="mini">
					<el-form-item :label="get_title(one_question)">
						<el-input
								v-model="answer[`${one_question.id}`]"
								placeholder="请输入内容"
								size="mini"
								@input="handleChange(one_question)"
								:type="one_question.mode === 2 ? 'text' : 'textarea'"
						>
						</el-input>
					</el-form-item>
				</el-form>

			</div>

			<question-item v-if="one_question.children && one_question.children.length > 0"
						   :question="one_question.children" :answer="answer" :parent="one_question"></question-item>
		</div>

		<!--		 递归渲染子问题 -->
		<!--		<div v-for="one_question in question">-->
		<!--			-->
		<!--		</div>-->

	</div>
</template>

<script>

export default {
	name: 'QuestionItem',
	props: {
		question: [],
		answer: {},
		parent: null,
	},
	data() {
		return {
			selectedOptions: [], // 多选题的选择结果
			freeText: '', // 文本输入的内容
		};
	},
	methods: {
		get_class(one_question) {
			if (one_question.mode === 3 || one_question.title_number) {
				if (!one_question.title_number) {
					if (this.parent !== null) {
						// console.log(this.parent, this.parent.title)
						if (this.parent.title) {
							return "child-title-op"
						} else {
							return "child-title-op-not-title"
						}
					}
					return "child-title-op"
				} else {
					return "child-title"
				}
			} else {
				return "child-title-source"
			}
		},
		get_display_style(one_question) {
			if (one_question.mode === -1 && !one_question.title) {
				return `display: flex;`
			} else if ((one_question.mode === 3 && !one_question.title_number)) {
				return `display: inline-block;`
			} else
				return ``
		},
		get_color_style(one_question) {
			if (one_question.title_number || one_question.mode === -1) {
				if (!one_question.title) {
					return `color: black;margin-right: 0;`
				}
				return `color: black;`
			} else
				return ``
		},
		get_title(one_question) {
			return one_question.title_number
					? `${one_question.title_number}  ${one_question.title}`
					: `${one_question.title}`
		},
		handleChange(one_question) {
			// console.log("handleChange", one_question.id, this.answer[`${one_question.id}`])
			if (this.answer[`${one_question.id}`]) {
				for (const clear_id of one_question.clear_ids) {
					// console.log("clear_id", clear_id)
					this.answer[`${clear_id}`] = ""
				}
			}
		}
	},
};
</script>

<style scoped>
.child-title-source {
	margin-top: 10px;
	width: inherit;
}

.child-title {
	margin-top: 10px;
	margin-left: 20px;
	width: inherit;
}

.child-title-op {
	margin-right: 50px;
	width: inherit;
	margin-top: 10px;
}

.child-title-op-not-title {
	margin-right: 50px;
	width: inherit;
	margin-top: -1px;
}

.custom-checkbox {
	display: flex;
	align-items: center;
}

/deep/ .el-checkbox__input {
	order: 2; /* 调整复选框的位置 */
	padding-left: 10px;
}

/deep/ .el-checkbox__label {
	padding-left: 0;
	white-space: normal;
	font-size: 18px;
	line-height: normal;
}

/* 自定义样式 */
/* 自定义样式 */
/deep/ .custom-checkbox .el-checkbox__inner {
	border: none !important; /* 去掉默认边框 */
	background-color: transparent !important; /* 去掉默认背景 */
	width: 1em; /* 调整宽度 */
	height: 1em; /* 调整高度 */
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1em; /* 调整字体大小 */
	position: relative; /* 设置相对定位 */
}

/* 未选中状态 */
/deep/ .custom-checkbox .el-checkbox__inner::before {
	content: "(    )";
	color: #000; /* 未选中时括号颜色 */
	position: absolute;
	top: 0;
	left: 0;
	white-space: pre
}

/* 选中状态 */
/deep/ .custom-checkbox .el-checkbox__inner::after {
	content: "( ✓ )";
	color: #000; /* 选中时括号颜色 */
	position: absolute;
	top: 0;
	left: 0;
	opacity: 0; /* 默认不显示 */
	white-space: pre
}

/* 当选中时，显示右括号 */
/deep/ .custom-checkbox.is-checked .el-checkbox__inner::after {
	opacity: 1; /* 显示右括号 */
	transform: rotate(0deg) scaleY(1);
}

/* 当选中时，隐藏左括号 */
/deep/ .custom-checkbox.is-checked .el-checkbox__inner::before {
	opacity: 0; /* 隐藏左括号 */
}

/* 鼠标悬停样式（可选） */
/deep/ .custom-checkbox .el-checkbox__inner:hover::before, .custom-checkbox .el-checkbox__inner:hover::after {
	color: #409eff; /* 悬停时括号颜色 */
}
</style>