# 五分钟演示讲稿

这是一个给药物安全研究人员使用的资料核查原型。例如：两项研究对同一种药物的心血管风险看起来有不同结论，研究人员需要先弄清研究对象、研究方法和出处，而不是直接让聊天机器人给一个确定答案。

1. 打开网页，点击 **Try a saved example**。这会显示一次真实模型运行留下的结果，页面明确写着 Saved run。
2. 左边是研究草稿，右边是检索到的资料。展开某条结论下面的出处，能看到短引文、来源日期和原文链接。
3. 展开 **drafted claims withheld**，查看哪些初稿内容没有通过检查。被拦下不一定说明事实一定错误，也可能是引文被模型改写、无法精确匹配。
4. 展开 **Inspect the agent’s tool calls**，查看模型实际选择的检索问题、资料类型和返回的片段编号。
5. 回到上方，点击 **Run agent**。这次会实际请求模型，而不是播放示例。也可以改问 “Who was enrolled in the ORAL Surveillance trial?”。
6. 把日期改到 2020 年，再运行：这份小资料集在该日期前没有资料，应该保留“资料不足”的结论。

## 技术如何分工

- **LangGraph**：安排“计划检索、取资料、写草稿、复核、返回”的步骤，并在步骤之间传递状态。
- **模型 API**：模型决定检索哪些问题、从查到的资料里整理结论，并在另一次调用中复核。
- **Chroma 与 embeddings**：把段落和问题转换成向量，找到语义接近的内容；系统同时参考关键词重合度。
- **Python 检查代码**：确认引用编号确实存在、引用文字确实在原文中、资料日期没有超出用户限制。
- **FastAPI 与 Cloud Run**：提供网页与后台服务，把实际运行进度传给浏览器。
- **Paper MCP**：用于设计界面。它不负责检索资料，也不执行 Agent。

## 面试时可以怎样说

“I built an independent prototype to practice evidence-grounded agent workflows. The model plans bounded searches, drafts claims from public sources, and checks support before the result is shown. I also added deterministic citation and date checks, plus a small evaluation suite.”

接着说明边界：“The live version uses OpenAI. I implemented a Bedrock Converse adapter, but have not yet verified it with an AWS account. This is a learning project, not production pharmacovigilance experience.”

不要把“通过引用检查”说成“结论百分之百正确”。这次 30 个问题的评测能证明实际调用、出处检查、日期过滤和部分拒答行为运转正常，不能代替专业医学验证。
