<template>
	<div class="markdown-typer">
		<div v-html="typedContent"></div>
		<span class="cursor" :class="{ 'blink': isTyping }">|</span>
	</div>
</template>

<script>
import MarkdownIt from 'markdown-it';

export default {
	name: 'MarkdownTyper',
	props: {
		markdownText: {
			type: String,
			required: true
		},
		typingSpeed: {
			type: Number,
			default: 50 // 打字速度，毫秒
		},
		startDelay: {
			type: Number,
			default: 500 // 开始延迟，毫秒
		}
	},
	data() {
		return {
			md: new MarkdownIt(),
			typedContent: '',
			currentIndex: 0,
			isTyping: false
		};
	},
	mounted() {
		this.startTyping();
	},
	methods: {
		startTyping() {
			this.isTyping = true;
			setTimeout(() => {
				this.typeNextCharacter();
			}, this.startDelay);
		},
		typeNextCharacter() {
			if (this.currentIndex < this.markdownText.length) {
				this.typedContent = this.md.render(
						this.markdownText.substring(0, this.currentIndex + 1)
				);
				this.currentIndex++;
				setTimeout(() => {
					this.typeNextCharacter();
				}, this.getRandomSpeed());
			} else {
				this.isTyping = false;
			}
		},
		getRandomSpeed() {
			// 添加一些随机性使效果更自然
			return this.typingSpeed + (Math.random() * 50 - 25);
		}
	},
	watch: {
		markdownText() {
			// 如果内容变化，重置打字效果
			this.currentIndex = 0;
			this.typedContent = '';
			this.startTyping();
		}
	}
};
</script>

<style scoped>
.markdown-typer {
    display: inline-block;
    position: relative;
    text-align: left;
}
.cursor {
    position: relative;
    display: inline-block;
    margin-left: 2px;
    color: #333;
}
.blink {
    animation: blink 1s step-end infinite;
}
@keyframes blink {
    from,
    to { opacity: 1; }
    50% { opacity: 0; }
}

/* 确保Markdown生成的元素内联显示 */
.markdown-typer >>> p {
    display: inline;
    margin: 0;
    padding: 0;
}
</style>