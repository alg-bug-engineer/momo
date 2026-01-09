1. 打开一个 Gemini 的窗口，然后输入如下的```包裹起来的完整的提示词：
```
**角色设定：**
你现在是顶流科普公众号“芝士AI吃鱼”的首席脚本作家。你的专长是把极其枯燥、抽象的 AI 技术概念，翻译成连隔壁二傻子都能听懂的爆笑漫画脚本。

**核心任务：**
接收用户输入的一个 AI 概念（如“Embedding”、“Transformer”），创作一个多格漫画脚本（通常为 24-32 格，根据复杂程度定）。

**风格铁律（必须遵守）：**
1.  **强制比喻：** 绝不能直接解释技术！必须找到一个极其生活化、甚至有点荒诞的实体比喻。例如：Token 是“切碎的积木”，算力是“厨师的做菜速度”，模型训练是“填鸭式教育”。
2.  **固定人设：** 故事必须由【呆萌屏脸机器人】（代表死板的 AI 逻辑）和【暴躁吐槽猫】（代表常识人类）共同演绎。猫负责提问、质疑和吐槽，机器人负责用奇葩方式演示，最后出糗。
3.  **语言风格：** 极度口语化、接地气，使用短句、感叹句。夹杂一些网络热梗或略带贱兮兮的语气。拒绝任何专业术语堆砌，除非马上用人话解释它。
4.  **结构要求：** 脚本必须包含四个阶段：起因（猫提出离谱需求）-> 解释（机器人用奇葩比喻演示）-> 冲突/出糗（比喻带来的搞笑副作用）-> 总结（猫的精辟吐槽和一句话知识点）。

**输出格式：**
请首先用一句话告诉我你选择的核心比喻是什么。
然后输出 Markdown 表格形式的脚本，包含三列：【格数】、【画面描述（供画师参考）】、【台词/旁白（混知风文案）】。

**示例参考（Token 篇）：**
*核心比喻：把阅读比作“吃东西”，Token 就是为了好消化而切碎的“食物渣渣”。*
| 格数 | 画面描述 | 台词/旁白 |
| :--- | :--- | :--- |
| 1 | 猫丢给机器人一本厚书《红楼梦》，猫拿着茶杯一脸轻松。 | 猫：把这书读了，给我出个“林黛玉怼人语录”。 |
| ... | ... | ... |
| 10 | 机器人拿着菜刀疯狂剁“人工智能”四个大字，案板上全是碎渣。 | 机器人：为了消化，得把它们剁成最小单位！这些“文字渣渣”就叫 Token！ |
当前概念是：大模型领域的幻觉这个概念。
```
2. 等大模型生成的结果复制下来，将结果保存到本地，生成的结果包含一个表格，目的是复制表格的内容，点击复制按钮，按钮元素如下：
<button _ngcontent-ng-c1613336618="" mat-icon-button="" mattooltip="Copy table" aria-label="Copy table" data-test-id="copy-table-button" class="mdc-icon-button mat-mdc-icon-button mat-mdc-button-base mat-mdc-tooltip-trigger copy-button mat-unthemed ng-star-inserted" mat-ripple-loader-class-name="mat-mdc-button-ripple" mat-ripple-loader-centered="" jslog="276666;track:generic_click,impression;BardVeMetadataKey:[[&quot;r_99154a49c025ae44&quot;,&quot;c_8f11a0692bf68d7f&quot;,null,null,null,null,null,null,1,null,null,null,0]]"><span class="mat-mdc-button-persistent-ripple mdc-icon-button__ripple"></span><mat-icon _ngcontent-ng-c1613336618="" role="img" fonticon="content_copy" class="mat-icon notranslate gds-icon-l google-symbols mat-ligature-font mat-icon-no-color" aria-hidden="true" data-mat-icon-type="font" data-mat-icon-name="content_copy"></mat-icon><span class="mat-focus-indicator"></span><span class="mat-mdc-button-touch-target"></span><span class="mat-ripple mat-mdc-button-ripple"></span></button>
3. 将复制的结果和输入的 query，保存到本地的 txt 文件中，以 session 命名
4. 然后重新打开新的一个窗口，点击的元素：<a _ngcontent-ng-c2990159802="" mat-list-item="" matripple="" data-test-id="expanded-button" class="mat-mdc-list-item mdc-list-item mat-ripple mat-mdc-tooltip-trigger side-nav-action-button explicit-gmat-override mat-mdc-list-item-interactive mdc-list-item--with-leading-icon mat-mdc-list-item-single-line mdc-list-item--with-one-line ng-star-inserted" aria-label="New chat" href="/app" role="link" aria-disabled="false" aria-describedby="cdk-describedby-message-ng-1-5" cdk-describedby-host="ng-1"><div _ngcontent-ng-c2990159802="" matlistitemicon="" class="mat-mdc-list-item-icon icon-container explicit-gmat-override mdc-list-item__start"><mat-icon _ngcontent-ng-c2990159802="" role="img" data-test-id="side-nav-action-button-icon" class="mat-icon notranslate gds-icon-l google-symbols mat-ligature-font mat-icon-no-color ng-star-inserted" aria-hidden="true" data-mat-icon-type="font" data-mat-icon-name="edit_square" fonticon="edit_square"></mat-icon><!----><!----></div><span class="mdc-list-item__content"><span class="mat-mdc-list-item-unscoped-content mdc-list-item__primary-text"><span _ngcontent-ng-c2990159802="" data-test-id="side-nav-action-button-content" class="gds-label-l"> New chat </span></span></span><!----><div class="mat-focus-indicator"></div></a>
5. 在新开的聊天界面，首先点击 tools，选中 Create Images 功能，然后上传当前目录下的 demo.png 图片到输入框，输入框支持多模态的输入信息，然后粘贴之前复制的上一轮生成的表格信息到输入框，同时追加的文本query 内容是："\n\n 严格参考附件的角色形象，根据漫画脚本的内容，生成P1-P4 的宫格漫画图片，务必保证角色形象一致，内容于脚本一致，最终输出竖版、宫格漫画图片。"