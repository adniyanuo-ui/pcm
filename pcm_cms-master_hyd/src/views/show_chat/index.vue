<template>
	<div>
		<el-dialog :visible.sync="llm_visible" width="80%" top="2vh" :title="`${chat.model_name}(${chat.runtime}s)`">
			<div>
				<div class="title">system:</div>
				<div class="chunk inp">
					{{ chat.system }}
				</div>

				<div class="title">user:</div>
				<div class="chunk inp">
					{{ chat.user }}
				</div>
			</div>

			<div>
				<div class="title" v-if="chat.reasoning">深度思考:</div>
				<div class="chunk" v-if="chat.reasoning">
					<div v-html="renderedMarkdown(chat.reasoning)"></div>
				</div>

				<div class="title">模型输出:</div>
				<div class="chunk">
					<div v-html="renderedMarkdown(chat.output)"></div>
				</div>

				<div class="title" v-if="chat.revise_output">人工修改输出:</div>
				<div class="chunk" v-if="chat.revise_output">
					<div v-html="renderedMarkdown(chat.revise_output)"></div>
				</div>

			</div>
		</el-dialog>

		<div>
			<el-table :data="data.results" style="width: 100%;" border highlight-current-row class="custom-table">
				"id", "r_id", "star", "revise_output", "patient""model_name", "runtime", "prompt_tokens",
				"completion_tokens"
				<el-table-column prop="id" label="id" width="50"/>
				<el-table-column prop="patient" label="姓名">
					<template #default="scope">
						<div class="ellipsis" style="cursor: pointer;" @click="on_open_llm(scope.row)">
							{{ scope.row.patient }}
						</div>
					</template>
				</el-table-column>
				<el-table-column prop="star" label="星级"/>
				<el-table-column prop="model_name" label="模型"/>
				<el-table-column prop="runtime" label="请求时间"/>
				<el-table-column prop="prompt_tokens" label="问Token数"/>
				<el-table-column prop="completion_tokens" label="答Token数"/>
<!--				<el-table-column label="操作" width="100">-->
<!--					<template #default="scope">-->
<!--						<el-button round size="mini" @click="on_open_llm(scope.row)">查看模型输出</el-button>-->
<!--					</template>-->
<!--				</el-table-column>-->
			</el-table>

			<el-footer class="footer">
				<el-pagination layout="prev, pager, next" :total="data.count" :current-page.sync="current_page" :page-size="form.limit"
							   @current-change="handleCurrentChange">
				</el-pagination>
			</el-footer>
		</div>
	</div>
</template>

<script>
import {on_get_data} from "@/api/patient";
import {on_get_llm_data, show_llm_chat, show_llm_chat_one, star} from "@/api/llm";
import store from "@/store";
import "github-markdown-css";
import MarkdownIt from "markdown-it";
import {Message} from "element-ui";
// import { marked } from 'marked';

export default {
	name: 'show_chat',
	components: {},
	data() {
		return {
			form: {
				"limit": 20,
				"offset": 0,
			},
			data: {},
			current_page: 1,
			llm_visible: false,

			// 模型输出
			chat: {
				"reasoning": "",
				"output": "",
			},
			// 打字机相关
			md: new MarkdownIt(),
		}
	},
	methods: {
		renderedMarkdown(txt) {
			return this.md.render(txt);
		},
		async handleCurrentChange(val) {
			this.current_page = val
			await this.get_data()
		},
		async get_data() {
			this.form["offset"] = (this.current_page - 1) * this.form.limit
			const resp = await show_llm_chat(this.form)
			this.data = resp.data;
		},
		on_open_llm(row) {
			show_llm_chat_one(row.r_id).then(response => {
				this.chat = response.data
				this.llm_visible = true;
			})
		}
	},
	mounted() {
		this.get_data()
	},
}
</script>

<style lang="scss" scoped>
::v-deep .el-dialog__body {
    padding: 10px 20px;
}
.chunk {
    border-radius: 5px;
    background-color: rgb(216, 214, 214);
    padding: 5px;
    margin-bottom: 10px;
    max-height: 40vh;
    overflow-y: auto;
}
.inp {
    white-space: pre;
}
.title {
    font-weight: 500;
}
</style>