/**
 * intentDetection.ts 单元测试
 */

import { describe, it, expect } from "vitest";
import {
  detectIntent,
  extractSearchQuery,
  extractConcept,
  extractUpdateTarget,
  extractDeleteTarget,
  extractReviewParams,
  getHelpMessage,
  intentConfig,
  intentIcons,
} from "./intentDetection";

describe("detectIntent", () => {
  describe("create 意图", () => {
    it("应该识别默认创建意图", () => {
      expect(detectIntent("明天下午3点开会")).toBe("create");
      expect(detectIntent("记录今天的学习笔记")).toBe("create");
    });

    it("应该识别包含创建关键词的文本", () => {
      expect(detectIntent("新建一个项目")).toBe("create");
      expect(detectIntent("创建一个任务")).toBe("create");
      expect(detectIntent("记一下这个想法")).toBe("create");
    });
  });

  describe("read 意图", () => {
    it("应该识别搜索意图", () => {
      expect(detectIntent("帮我找 MCP 的笔记")).toBe("read");
      expect(detectIntent("搜索 RAG 相关内容")).toBe("read");
      expect(detectIntent("有没有关于 Agent 的笔记")).toBe("read");
    });

    it("应该识别查看意图", () => {
      expect(detectIntent("查看今天的任务")).toBe("read");
      expect(detectIntent("显示所有项目")).toBe("read");
      expect(detectIntent("列出待办事项")).toBe("read");
    });
  });

  describe("update 意图", () => {
    it("应该识别状态更新意图", () => {
      expect(detectIntent("把 MCP 笔记的状态改为完成")).toBe("update");
      expect(detectIntent("标记测试任务为完成")).toBe("update");
      expect(detectIntent("更新项目状态")).toBe("update");
    });
  });

  describe("delete 意图", () => {
    it("应该识别删除意图", () => {
      expect(detectIntent("删除测试任务")).toBe("delete");
      expect(detectIntent("移除临时记录")).toBe("delete");
      expect(detectIntent("删掉这个条目")).toBe("delete");
    });
  });

  describe("knowledge 意图", () => {
    it("应该识别知识图谱意图", () => {
      expect(detectIntent("MCP 的知识图谱")).toBe("knowledge");
      expect(detectIntent("查看 RAG 的相关概念")).toBe("knowledge");
      expect(detectIntent("展示 Agent 的概念图")).toBe("knowledge");
    });
  });

  describe("review 意图", () => {
    it("应该识别回顾意图", () => {
      expect(detectIntent("今天做了什么")).toBe("review");
      expect(detectIntent("本周进度")).toBe("review");
      expect(detectIntent("月报")).toBe("review");
      expect(detectIntent("回顾")).toBe("review");
    });
  });

  describe("help 意图", () => {
    it("应该识别帮助意图", () => {
      expect(detectIntent("帮助")).toBe("help");
      expect(detectIntent("能做什么")).toBe("help");
      expect(detectIntent("怎么用")).toBe("help");
      expect(detectIntent("使用说明")).toBe("help");
    });
  });

  describe("意图优先级", () => {
    it("help 意图应该有最高优先级", () => {
      expect(detectIntent("帮助我创建任务")).toBe("help");
    });

    it("review 意图应该优先于 create", () => {
      expect(detectIntent("回顾今天的创建记录")).toBe("review");
    });

    it("knowledge 意图应该优先于 read", () => {
      expect(detectIntent("搜索知识图谱")).toBe("knowledge");
    });
  });
});

describe("extractSearchQuery", () => {
  it("应该从搜索文本中提取查询词", () => {
    expect(extractSearchQuery("帮我找 MCP 的笔记")).toBe("MCP 的笔记");
    expect(extractSearchQuery("搜索 RAG")).toBe("RAG");
    expect(extractSearchQuery("有没有 Agent")).toBe("Agent");
  });

  it("应该处理没有关键词的文本", () => {
    expect(extractSearchQuery("任意文本")).toBe("任意文本");
  });
});

describe("extractConcept", () => {
  it("应该从知识图谱文本中提取概念", () => {
    expect(extractConcept("MCP 的知识图谱")).toBe("MCP");
    expect(extractConcept("RAG 的相关概念")).toBe("RAG");
    expect(extractConcept("查看 Agent 的图谱")).toBe("Agent");
  });

  it("应该处理没有关键词的文本", () => {
    expect(extractConcept("任意文本")).toBe("任意文本");
  });
});

describe("extractUpdateTarget", () => {
  describe("状态更新", () => {
    it("应该提取状态更新目标", () => {
      const result = extractUpdateTarget("把 MCP 笔记的状态改为完成");
      expect(result.query).toBe("MCP 笔记");
      expect(result.field).toBe("status");
      expect(result.value).toBe("complete");
    });

    it("应该映射中文状态到英文", () => {
      const result = extractUpdateTarget("把任务标记为进行中");
      expect(result.field).toBe("status");
      expect(result.value).toBe("doing");
    });

    it("应该识别暂停状态", () => {
      const result = extractUpdateTarget("把任务设为暂停");
      expect(result.field).toBe("status");
      expect(result.value).toBe("paused");
    });
  });

  describe("标签更新", () => {
    it("应该提取标签更新目标", () => {
      const result = extractUpdateTarget("给学习添加标签 AI");
      expect(result.query).toBe("学习");
      expect(result.field).toBe("tags");
      expect(result.value).toBe("AI");
    });

    it("应该处理'为...添加标签'格式", () => {
      const result = extractUpdateTarget("为项目添加标签重要");
      expect(result.query).toBe("项目");
      expect(result.field).toBe("tags");
      expect(result.value).toBe("重要");
    });
  });

  describe("通用更新", () => {
    it("应该处理无法匹配的文本", () => {
      const result = extractUpdateTarget("随便说点什么");
      expect(result.query).toBe("随便说点什么");
      expect(result.field).toBe("");
    });
  });
});

describe("extractDeleteTarget", () => {
  it("应该提取删除目标", () => {
    expect(extractDeleteTarget("删除测试任务").query).toBe("测试任务");
    expect(extractDeleteTarget("移除临时记录").query).toBe("临时记录");
    expect(extractDeleteTarget("删掉这个条目").query).toBe("这个条目");
  });

  it("应该处理没有关键词的文本", () => {
    expect(extractDeleteTarget("任意文本").query).toBe("任意文本");
  });
});

describe("extractReviewParams", () => {
  it("应该识别日报", () => {
    const result = extractReviewParams("今天做了什么");
    expect(result.type).toBe("daily");
  });

  it("应该识别周报", () => {
    const result = extractReviewParams("本周进度");
    expect(result.type).toBe("weekly");
  });

  it("应该识别月报", () => {
    const result = extractReviewParams("月报");
    expect(result.type).toBe("monthly");
  });

  it("应该识别昨天的回顾", () => {
    const result = extractReviewParams("昨天做了什么");
    expect(result.type).toBe("daily");
    expect(result.date).toBeDefined();
    // 验证日期是昨天
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(result.date).toBe(yesterday.toISOString().split("T")[0]);
  });
});

describe("getHelpMessage", () => {
  it("应该返回帮助信息", () => {
    const help = getHelpMessage();
    expect(help).toContain("我能帮你做什么");
  });
});

describe("intentConfig", () => {
  it("应该包含所有意图的配置", () => {
    expect(intentConfig.create).toBeDefined();
    expect(intentConfig.read).toBeDefined();
    expect(intentConfig.update).toBeDefined();
    expect(intentConfig.delete).toBeDefined();
    expect(intentConfig.knowledge).toBeDefined();
    expect(intentConfig.review).toBeDefined();
    expect(intentConfig.help).toBeDefined();
  });
});

describe("intentIcons", () => {
  it("应该包含所有意图的图标", () => {
    expect(intentIcons.create).toBeDefined();
    expect(intentIcons.read).toBeDefined();
    expect(intentIcons.update).toBeDefined();
    expect(intentIcons.delete).toBeDefined();
    expect(intentIcons.knowledge).toBeDefined();
    expect(intentIcons.review).toBeDefined();
    expect(intentIcons.help).toBeDefined();
  });
});
