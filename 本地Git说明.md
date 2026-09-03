# 本地 Git 说明

当前工作环境将项目根目录的 `.git/` 以只读 `tmpfs` 方式挂载为占位目录，无法写入、卸载或覆盖。为保证所有有价值成果仍进入版本管理，本项目暂时使用工作区内的 `.git-local/` 作为实际 Git 目录，并在 `.gitignore` 中忽略它自身。

常用命令：

```bash
git --git-dir=.git-local --work-tree=. status
git --git-dir=.git-local --work-tree=. log --oneline
```

当前分支为 `main`，已配置并推送至：

```text
origin  https://github.com/adniyanuo-ui/pcm.git
```

## 恢复为标准 `.git/`

离开当前只读挂载环境后，在项目根目录执行：

```bash
# 先确认 .git 不再是挂载点，且仍为空占位目录
mountpoint .git
find .git -mindepth 1 -maxdepth 1 -print

# mountpoint 返回“不是挂载点”且 find 无输出时再执行
rmdir .git
mv .git-local .git
git status
```

转换只是 Git 元数据目录更名，不会改变已提交的项目文件或远端记录。
