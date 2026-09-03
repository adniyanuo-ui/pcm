# 本地 Git 说明

当前工作环境提供的 `.git/` 是只读挂载占位目录，无法写入 Git 对象。为保证所有有价值成果仍进入本地版本管理，本项目使用工作区内的 `.git-local/` 作为实际 Git 目录，并在 `.gitignore` 中忽略它自身。

常用命令：

```bash
git --git-dir=.git-local --work-tree=. status
git --git-dir=.git-local --work-tree=. log --oneline
```

当前分支为 `main`。尚未配置 GitHub remote，也没有向外部推送。后续确定个人 GitHub 仓库地址、可见性和认证方式后，再配置远端并推送。
