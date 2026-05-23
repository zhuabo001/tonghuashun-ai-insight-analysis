# scripts-design


## 信息源
### schema for feed

- `name`：来源名称
- `url`：RSS 地址
- `lang`：语言，`zh` 或 `en`
- `priority`：来源优先级
- `ai_only`：是否视为 AI 专用源



### 中文 ai 信源站点
| 来源 | RSS 地址 | 语言 | priority | ai_only |
| --- | --- | --- | --- | --- |
| 机器之心 | `https://www.jiqizhixin.com/feed` | zh | 1 | true |
| 量子位 | `https://www.qbitai.com/feed` | zh | 1 | true |


这些来源本身以 AI 内容为主，但要求标题或摘要命中 AI 白名单关键词，避免混入和 AI 无关的周边内容

### 英文 ai 信源站点
| 来源 | RSS 地址 | 语言 | priority | ai_only |
| --- | --- | --- | --- | --- |
| TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/feed/` | en | 1 | true |
| The Verge AI | `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | en | 1 | true |

同样需要经由ai白名单进行校验，避免混入噪声

### 英文 ai/社区聚合源
| 来源 | RSS 地址 | 语言 | priority | ai_only |
| --- | --- | --- | --- | --- |
| Hacker News AI | `https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT+OR+%22artificial+intelligence%22+OR+%22machine+learning%22&points=100` | en | 2 | true |

这部分也要进行白名单校验，避免混入无关内容

## 信源黑名单

黑名单覆盖的典型类别包括：

- 美容护肤：护发、美妆、护肤、彩妆、美容、美甲、美发
- 汽车普通内容：汽车大灯、车灯、轮胎、发动机、变速箱
- 生活消费：美食、菜谱、烹饪、餐厅、外卖、旅游、酒店、机票、签证、景点
- 游戏娱乐：游戏攻略、游戏评测、手游、网游、电竞、明星、八卦、综艺、电影
- 健康医疗泛内容：健康养生、药品、保健品、中医、感染、肠胃、肿瘤、癌症、疫苗
- 房产家居：房产、装修、家具、家电
- 财经股市：A股、B股、港股、美股、股市、涨跌、沪指、深成指、创业板指、三大指数
- 部分非 AI 相关公司或概念：中国移动、中国联通、工商银行、建设银行等
- 非 AI 语境下的汽车品牌：理想汽车、蔚来、小鹏、比亚迪、特斯拉、问界、极氪等

黑名单优先级**最高**。即使来源是 AI 专用源，**只要命中黑名单，也会被过滤掉**！


## 中文源的ai白名单
中文关键词覆盖了模型、技术、产品、厂商、算力和应用方向。

典型关键词包括：

- 通用 AI 词：AI、人工智能、大模型、LLM、GPT、ChatGPT
- 模型产品：Claude、Gemini、Llama、DeepSeek、Kimi、豆包、通义、文心、智谱、百川、MiniMax、阶跃星辰
- 技术方向：深度学习、机器学习、神经网络、自然语言、NLP、计算机视觉、CV、生成式、AIGC、AGI、Transformer、扩散模型
- Agent 方向：智能体、Agent
- 多模态/生成工具：Stable Diffusion、Midjourney、DALL-E、Sora、可灵、seedance
- 机器人和自动驾驶：机器人、具身智能、自动驾驶、世界模型、vla模型
- 语音方向：语音识别、TTS、ASR
- 算力和芯片：英伟达、NVIDIA、GPU、算力、芯片、H100、A100、寒武纪、摩尔线程、砺算科技、沐曦科技、光芯片
- 厂商：OpenAI、Anthropic、Google AI、Meta AI、微软 AI、百度 AI、阿里 AI、腾讯 AI、字节 AI、华为 AI、美团ai、快手ai、月之暗面、minimax、智谱、科大讯飞、商汤、旷视


## 英文源的ai白名单
英文关键词覆盖了 AI 基础概念、模型、训练推理和厂商。

典型关键词包括：

- 通用 AI 词：AI、artificial intelligence、machine learning、deep learning、LLM
- 模型产品：GPT、ChatGPT、Claude、Gemini、Llama
- 技术方向：transformer、diffusion、generative、AIGC、AGI、agent、neural network、NLP
- 厂商：OpenAI、Anthropic、Google AI、Meta AI、Microsoft AI
- 算力训练：NVIDIA、GPU、inference、training、fine-tuning、RLHF
- 生成工具：Stable Diffusion、Midjourney、DALL-E、Sora、Whisper




## 信息获取流程

**信息统一记录在`项目根目录下的/data/news.json`中**

处理流程如下：

```text
读取 RSS_SOURCES 配置
    ↓
逐个 RSS 源拉取 feed
    ↓
每个源最多处理前 20 条 entry
    ↓
过滤 3 天以前的旧新闻
    ↓
清洗标题和摘要
    ↓
按黑名单 + AI 白名单判断是否 AI 相关
    ↓
生成稳定新闻 ID
    ↓
与已有 data/news.json 合并
    ↓
按 ID 去重
    ↓
对历史数据按最新规则重新清洗
    ↓
按发布时间排序
    ↓
最多保留 300 条
    ↓
写回 data/news.json
```

## 信息清洗
### 1. 空值处理
如果输入为空，直接返回空字符串，这可以避免后续正则处理空值时报错。

### 2. 去除html标签
脚本使用正则删除 HTML 标签，RSS 中的 `summary` 或 `description` 经常包含 `<p>`、`<img>`、`<a>` 等标签，这一步会将其转成纯文本

### 3. 压缩多余空白
把连续空白压缩为一个空格，并去掉首尾空白，这样可以统一标题和摘要格式，避免换行、制表符影响关键词匹配。

### 4. 处理常见html实体
替换了常见 HTML 实体：

- `&amp;` → `&`
- `&lt;` → `<`
- `&gt;` → `>`
- `&quot;` → `"`
- `&#39;` → `'`
- `&nbsp;` → 空格

### 5. 摘要截断
清洗后的文本最多保留前 300 个字符，这是为了让 RSS 摘要保持轻量，避免将过长内容直接塞入 `news.json` 的 `summary` 字段


## 信息过滤
通过工具函数把标题和摘要拼接起来，并统一转成大写后匹配， 这样是为了让关键词匹配对英文大小写不敏感。


### rule 1 —— 黑名单优先
第一步先检查非 AI 黑名单。只要标题或摘要命中黑名单关键词，就直接排除！

### rule 2 —— 即使是ai信源也需要白名单确认
即使信源的schema中的`ai_only`是`true`, 也要求标题或摘要命中任意 AI 白名单关键词！
这么做的目的：

- 防止 AI 频道混入广告、活动、招聘、泛科技内容
- 防止 RSS 源实际内容和源名称不完全一致
- 保证进入 `news.json` 的内容至少有明确 AI 信号

### rule 3 —— 聚合源**必须**命中ai白名单
特指 `hacker news ai`这个信源，如果这个schema中的`ai_only` 为 `false`，脚本会分别检查中文和英文 AI 关键词。只要命中任意一个关键词，就认为是 AI 相关新闻。


### rule 4 —— 时间过滤
只保留最近 3 天内的 RSS 新闻， 如果如果 RSS entry 有`published_parsed`，并且发布时间早于 cutoff(datetime.now() - timedelta(days=3))，则跳过。
如果 entry 没有发布时间，脚本不会因为缺少发布时间而直接丢弃，而是继续处理，并将 `published` 设为 `None`。

### rule 5 —— 数量限制

每个 RSS 源最多只处理前 10 条 entry，这么做是为了：
- 降低单次采集成本
- 避免某个 RSS 源数据过多拖慢流程
- 配合 3 天时间窗口，保证主要处理近期内容

## 新闻id生成

每条新闻使用 URL 生成稳定 ID，同一个url生成同一个id，有了id方便后续数据去重

## 新闻格式
每条符合要求、经过过滤的新闻内容会被格式化为如下格式：
```json
{
  "id": "由 URL md5 生成的 12 位 ID",
  "title": "清洗后的标题",
  "url": "原文链接",
  "source": "来源名称",
  "lang": "zh/en",
  "priority": 1,
  "published": "ISO 格式发布时间或 null",
  "summary": "清洗并截断后的摘要",
  "collected_at": "采集时间"
}
```
其中：

- `id` 用于去重和后续页面生成
- `title` 用于展示、搜索和过滤
- `url` 指向原始来源
- `source` 标识媒体来源
- `lang` 标识语言
- `priority` 反映来源优先级
- `published` 用于排序
- `summary` 用于列表展示和 AI 相关性判断
- `collected_at` 记录采集时间


## 信息去重
**当且仅当在`data/news.json`已存在的前提下进行**。
采集完成后，脚本会读取已有的 `data/news.json`。

合并逻辑：

1. 读取已有新闻。
2. 提取已有新闻 ID。
3. 只保留本轮采集中 ID 不存在的新新闻。
4. 将旧新闻和新新闻合并。
5. 再次按 ID 去重。

这保证脚本可以重复运行，不会因为同一 RSS entry 被多次抓取而产生重复数据

### 对历史数据二次清理
脚本不仅过滤本轮新采集的数据，还会对已有历史数据重新应用当前规则，这样做是为了：
- 如果黑名单或白名单更新，旧数据也会被重新清理
- 避免早期规则较松时进入的脏数据长期留在 `news.json`
- 让数据集始终符合当前质量规则

## `news.json`中数据排序与条目数量上限
### 排序准则
先尝试做一次“中文优先 + 发布时间”的排序， 然后按发布时间倒序排序(最新到最旧)，由于第二次排序会成为最终主排序，因此最终结果主要是按 `published` 从新到旧排列。

### 上限条目数量
考虑到本项目的mvp版本属性，暂时规定条目数量的上限就是80条(五个source每个source10条entry，留了30条的冗余)。

### 数据写入位置
项目根目录下的 `data/news.json`.

## 后续补充
**本轮实现暂时可以先不考虑，本轮任务以稳定、低成本地获取高质量信息内容为主**。
考虑到后续需要实现一个日报分析engine，当前的信息条目的json结构可能仍然不足以支撑起后续的'分析'过程，可能需要添加例如：
- 导向： 偏正向还是负向
- 事件分类
- 重要性权重的权值
- 风险/机会判断

除了分析本身这个行为之外，还需要将分析的结果以可视化的形式进行输出和交付。
当然这将会留到下一轮去思考和实现。









