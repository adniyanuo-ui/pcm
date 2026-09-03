<template>
	<div>
		<el-dialog title="创建二维码" :visible.sync="dialog_visible" width="80%" top="2vh">
			<el-form :model="add_data" label-width="80px" style="padding: 20px;">

				<el-form-item label="备注" style="margin-bottom: 20px;">
					<el-input v-model="add_data.remark" placeholder="备注"></el-input>
				</el-form-item>

				<el-form-item label="问卷类型" style="margin-bottom: 20px;">
					<el-select v-model="add_data.data.q_type" placeholder="问卷类型" clearable>
						<el-option label="通用" value="common">通用</el-option>
						<el-option label="学校" value="school">学校</el-option>
						<el-option label="企业" value="company">企业</el-option>
						<el-option label="机关单位" value="gov">机关单位</el-option>
					</el-select>
				</el-form-item>

				<el-form-item label="医生" style="margin-bottom: 20px;">
					<el-select v-model="add_data.data.doctor_id" placeholder="医生" clearable>
						<el-option :label="item.username" :value="item.id" v-for="item in user">
							{{ item.username }}
						</el-option>
					</el-select>
				</el-form-item>

				<el-form-item style="margin-bottom: 20px;">
					<el-button type="success" @click="add_qr">创建</el-button>
				</el-form-item>
			</el-form>
		</el-dialog>

		<el-container>
			<el-header class="header">
				<el-form :inline="true" :model="form" class="demo-form-inline" size="mini">
					<el-form-item>
						<el-button type="primary" @click="onSearch">查询</el-button>
					</el-form-item>

					<el-form-item>
						<el-button type="success" @click="dialog_visible = true">创建</el-button>
					</el-form-item>
				</el-form>
			</el-header>

			<el-main>
				<el-table :data="data.results" style="width: 100%;" border highlight-current-row class="custom-table">
					"id", "data", "remark", "img", "doctor", "q_type"
					<el-table-column prop="id" label="id" width="50"/>
					<el-table-column prop="remark" label="备注"/>
					<el-table-column prop="q_type" label="问卷类型" width="100"/>
					<el-table-column prop="doctor" label="医生" width="100"/>

					<el-table-column label="二维码" width="200">
						<template #default="scope">
							<el-image
									style="width: 100px; height: 100px;"
									:src="scope.row.img"
									:preview-src-list="[scope.row.img]">
							</el-image>
						</template>
					</el-table-column>

					<el-table-column label="操作" width="100">
						<template #default="scope">
							<el-button round size="mini" @click="delete_data(scope.row)">删除</el-button>
							<!--							<el-button round size="mini" @click="on_open_llm(scope.row)">AI自动推荐</el-button>-->
						</template>
					</el-table-column>
				</el-table>
			</el-main>

			<el-footer class="footer">
				<el-pagination layout="prev, pager, next" :total="data.count" :current-page.sync="current_page"
							   :page-size="form.limit"
							   @current-change="handleCurrentChange">
				</el-pagination>
			</el-footer>
		</el-container>
	</div>
</template>

<script>
import {on_get_data} from "@/api/patient";
import {on_get_llm_data, star} from "@/api/llm";
import store from "@/store";
import "github-markdown-css";
import MarkdownIt from "markdown-it";
import {Message} from "element-ui";
import * as XLSX from "xlsx";
import {on_add_qr, on_delete, on_get_qr} from "@/api/qr";
import {on_get_user} from "@/api/user";
// import { marked } from 'marked';

export default {
	name: 'patientList',
	components: {},
	data() {
		return {
			form: {
				limit: 10,
				offset: 0,
			},
			current_page: 1,
			data: {},

			add_data: {
				"remark": "",
				"data":{
					"q_type": "",
					"doctor_id": "",
				}
			},
			dialog_visible: false,
			user: [],
		}
	},
	methods: {
		async get_data() {
			this.form["offset"] = (this.current_page - 1) * this.form.limit
			const resp = await on_get_qr(this.form)
			this.data = resp.data;
		},
		async onSearch() {
			this.current_page = 1
			this.form["offset"] = 0
			await this.get_data()
		},
		async handleCurrentChange(val) {
			this.current_page = val
			await this.get_data()
		},
		add_qr() {
			on_add_qr(this.add_data).then(res => {
				this.get_data()
				this.dialog_visible = false
				this.add_data.remark = ''
				this.add_data.data.q_type = ''
				this.add_data.data.doctor_id = ''
			})
		},
		delete_data(row) {
			on_delete(row.id, {}).then(res => {
				this.get_data()
			})
		},
		get_user() {
			on_get_user().then(res => {
				this.user = res.data
			})
		}
	},
	mounted() {
		this.get_data()
		this.get_user()
	},
}
</script>

<style lang="scss" scoped>
::v-deep .el-form-item {
    margin-bottom: 0;
}
::v-deep .el-form--inline .el-form-item {
    margin-right: 20px;
}
::v-deep .el-table .el-table__cell {
    text-align: center;
}
::v-deep .el-textarea__inner {
    height: 100%;
}
::v-deep .el-dialog__body {
    padding: 10px 5px;
}
.header {
    display: flex;
    align-items: center;
}
.footer {
    display: flex;
    justify-content: center;
}
.ellipsis {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.chat-box {
    height: 80vh;
    overflow-y: auto;
    padding: 10px;
}
.message {
    width: 100%;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 5px;
    background-color: #f0f0f0;
    white-space: pre;
}
.message1 {
    width: 100%;
    display: inline-block;
    padding: 5px 10px;
    border-radius: 5px;
    background-color: #f0f0f0;
}
.textarea {
    width: 100%;
    height: 14vh;
}
.reasoner {
    border-radius: 5px;
    background-color: rgb(255, 255, 255);
    padding: 5px;
}
.typewriter-container * {
    font-family: monospace;
    position: relative;
    //width: auto;
}
.cursor {
    display: inline-block;
    width: 2px;
    height: 1em;
    background-color: black;
    animation: blink 1s step-end infinite;
}
@keyframes blink {
    from,
    to {
        opacity: 1;
    }
    50% {
        opacity: 0;
    }
}
</style>