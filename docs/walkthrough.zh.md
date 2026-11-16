# 五分钟演示讲稿

这是一个给药物安全研究人员使用的资料核查原型。例如：药物安全团队需要把两项研究、FDA 公告和药品说明书放在一起看，整理风险证据、监管表述与需要人工核查的问题。

1. 打开网页，在 **Explore six examples** 中选一个问题。这会直接显示一次真实模型运行留下的结果，页面明确写着 Saved run；不会重新调用模型。点 **Run agent** 才会新运行一次。
2. 左边的简报分为研究证据、FDA 公告、说明书和跨来源解读，右边是检索到的资料。顶部显示各类资料是否检索到，以及多少条结论通过检查。展开某条结论下面的出处，能看到短引文、来源日期和原文链接。
3. 展开 **drafted claims withheld**，查看哪些初稿内容没有通过检查。被拦下不一定说明事实一定错误，也可能是引文被模型改写、无法精确匹配。
4. 展开 **Inspect the agent’s tool calls**，查看模型实际选择的检索问题、资料类型和返回的片段编号。
5. 回到上方，点击 **Run agent**。这次会实际请求模型，而不是播放示例。也可以改问 “Who was enrolled in the ORAL Surveillance trial?”。
6. 把日期改到 2020 年，再运行：这份小资料集在该日期前没有资料，应该保留“资料不足”的结论。

## 技术如何分工

- **LangGraph**：安排“计划检索、取资料、写草稿、复核、返回”的步骤，并在步骤之间传递状态。
- **Vertex AI（Gemini）模型 API**：模型决定检索哪些问题、从查到的资料里整理结论，并在另一次调用中复核。
- **Chroma 与 Vertex text-embedding-005**：把段落和问题转换成向量，找到语义接近的内容；系统同时参考关键词重合度。
- **Python 检查代码**：确认引用编号确实存在、引用文字确实在原文中、资料日期没有超出用户限制。
- **FastAPI 与 Cloud Run**：提供网页与后台服务，把实际运行进度传给浏览器。
- **Paper MCP**：用于设计界面。它不负责检索资料，也不执行 Agent。

## 面试时可以怎样说

“I built an independent prototype to practice evidence-grounded agent workflows. The model plans bounded searches, drafts claims from public sources, and checks support before the result is shown. I also added deterministic citation and date checks, plus a small evaluation suite.”

接着说明边界：“The live version uses Vertex AI. I implemented a Bedrock Converse adapter, but have not yet verified it with an AWS account. This is a learning project, not production pharmacovigilance experience.”

不要把“通过引用检查”说成“结论百分之百正确”。历史 OpenAI 回归评测完成了 36 个问题中的 34 个，另两个遇到账户额度问题；该结果不能直接当作 Vertex 的效果指标。Vertex 另做了少量真实运行检查。这些检查不能代替专业医学验证。

## 资料是否实时联网？

目前使用预先加载的公开资料。导入程序下载文件、分段、生成 embeddings，再写入 Chroma 向量数据库。用户提问时，模型会真实生成检索计划，工具在这个索引中进行 RAG 检索。每次点击 Run agent 都是真实模型调用，但不会因此重新搜索互联网或刷新原始文档。

简报模式会分别查论文、FDA 公告、说明书三类来源，避免只查到论文就把它写成监管结论。若日期截止前没有某类资料，页面会显示缺口，而不会补造该部分。模型建议的待复核问题单独标明，不能当成已验证的事实。

三个概念可以这样区分：**Chroma** 是存储向量并查询相似段落的数据库；**RAG（Retrieval-Augmented Generation，检索增强生成）** 是先检索再根据资料回答的方法；**LangGraph Agent** 负责提出检索计划和串联工具、生成、检查步骤。准备资料时会调用 embedding API，回答时会调用生成模型 API，两者用途不同。

## 用六个例子讲给面试官听

| 页面上的例子 | 演示重点 |
|---|---|
| Prepare a safety-team brief | 完整流程：查论文、FDA 公告和说明书，再生成有出处的简报。 |
| Why do the studies differ? | 比较研究设计与人群，说明为什么不能只比较结论。 |
| Did FDA remove the warning? | 检查一篇研究是否真的能证明监管决定发生变化。 |
| What does the label say? | 查指定版本的说明书，区分说明书原文和研究解读。 |
| What was available in 2021? | 日期自动变为 2021-12-31，较新的论文和说明书被排除。 |
| What if no sources qualify? | 日期自动变为 2020-12-31，资料不足时不生成未经支持的结论。 |

六个场景使用同一份 tofacitinib 资料库。建议先演示第一个，再点 2021 年和 2020 年的例子，展示日期过滤以及资料缺口。切回其他例子时，日期也会恢复，避免用错范围。
