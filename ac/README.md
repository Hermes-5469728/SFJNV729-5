# AC Platform

我手头有 58 个开源工具，每个都很强，但它们不是一个妈生的，凑一起就互相不认得。AC 就是我在它们中间搭的桥——让数据从哪来、信不信得过、有没有过期，每一层都有记录。

环境：Python 3.14 / FastAPI / SQLite / ChromaDB / LangGraph

怎么用：
```
pip install litellm crewai mem0ai
python cli.py dispatch "失眠"
python ac_server.py
```

这东西怎么想的：

你说一句话进来，系统先看有没有匹配的专家（比如"失眠"就找心理医生），匹配到了再调 AI 模型生成回答，生成完了过 6 道检查——乱码没有、语法通不通、有没有安全隐患、有没有胡说八道。都过了才输出给你。

如果两条信息说的不一样（比如一个说布洛芬吃 200mg，一个说 800mg），系统不替你做决定，它把两条都摆出来，标上"这两条打架了，你来看"。宁可慢一点，不给错答案。

现状：
- DeepSeek 模型已经能调了，还接了 5 个模型等你填 Key
- 向量数据库 ChromaDB 就差一个模型文件下完就能用
- LangGraph（一个管多步骤任务的工具）装好了还没接上
- 详细安装计划在 `00-AC/MVP_SCALING_PLAN.md`
