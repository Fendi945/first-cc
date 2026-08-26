# 大一造园 · 公司官网源码

河北奥纳园林景观设计有限公司 / 大一造园 的官网静态页。

## 文件清单

| 文件 | 说明 |
|------|------|
| `yard-design.html` | 官网首页(落地页),页面标题「大一造园 · 把院子变成你想要的样子」 |
| `style.css` | 全站样式(Esther 不二设计风格) |
| `wechat-pay.png` | 付款二维码图 |
| `index.html` | 根路径跳转页(跳转 yard-design.html) |
| `README.md` | 本说明 |

> Google Fonts 为外链字体,无需打包。此文件夹自包含,可独立部署。此 5 个文件 = gh-pages 分支全部内容(2026-08-26 精简,删掉了原来 3082 个垃圾文件)。

## 线上地址

**https://fendi945.github.io/first-cc/yard-design.html**(主) / **https://fendi945.github.io/first-cc/**(跳转)

部署在 GitHub Pages,仓库 `Fendi945/first-cc`,分支 `gh-pages`(2026-08-26 重建成仅含部署文件)。

## 如何部署(WorkBuddy / 手动)

GitHub Pages 当前配置:Source = `gh-pages` 分支,路径 `/`。

**一键部署:** 把本文件夹内 4 个文件(`yard-design.html`、`style.css`、`wechat-pay.png`、`index.html`)复制到 `gh-pages` 分支根目录,commit 后 push 即可生效(有 `.nojekyll`,不会有 Jekyll 处理)。

```bash
# 示例:在 dayi-website 目录下
git add yard-design.html style.css wechat-pay.png index.html
git commit -m "feat: 大一造园官网更新"
git push origin gh-pages
```

> ⚠️ 历史坑:原 gh-pages 分支曾整仓库强推(3082 文件,含 .env/app.asar/build/),导致 GitHub Pages 构建失败(Page build failed)且泄露出敏感文件。2026-08-26 已重建为仅部署文件。以后**只准把 dayi-website/ 内容推 gh-pages**,别再把整个仓库推上去。

## 更新内容记录

- **2026-08-26**:首页 HERO 副标题删除「不做施工」(口径调整:不强调不做施工,实际承接施工管理陪跑)。
- **2026-08-26**:产品卡片调整——「最受欢迎」徽章从 199 档移到 499 档;199 档徽章改为「方向梳理」;199 档新增「1 次线上沟通(约 30 分钟)」;499 档沟通时间改为「约 60 分钟」;badge 样式改为对所有卡片生效(普通灰/热门黄)。
- **2026-08-26**:新增「设计服务」区(客户语言)——2000 硬化前落地定位图(带尺寸平面+排水走向+水电预埋点位+入口标高,师傅能直接施工)、4000 方案深化、6000 全套施工图;499 卡片补「不含水电预埋点位」+「适合方向还没定」+ 可抵差价升级;付款区档位选择器加入设计三档;FAQ 新增「场地整平要浇筑该买哪个」。
- **2026-08-26**:卡片对齐修复——所有 6 张卡加统一高度 `.tier-badge-slot` 徽章占位行,价格数字横向对齐;2000 描述简练为「浇筑前定好分区、排水、水电预埋,避免返工」;4000/6000 按公众号文章(庭院设计服务)加细:4000=逐区推敲+SU建模+效果图+植物材料风格落位,6000=土建/构筑物含挡土墙/给排水/电气/植物配置/铺装/灯光全专业;设计区底部加「100平内参考价,复杂项目1.5万-3万」。
- **2026-08-26**:三张卡补标注——9.9「一句话诊断」、4000「看院子落成后的效果」、6000「指导预算·施工」;移除 style.css 未打包的 HuiwenMincho @font-face(消除 404)。
- **2026-08-26**:gh-pages 分支重建——原 3082 文件整仓库强推导致构建失败,精简为仅 5 个部署文件(.nojekyll/index.html/style.css/wechat-pay.png/yard-design.html),构建恢复正常。
