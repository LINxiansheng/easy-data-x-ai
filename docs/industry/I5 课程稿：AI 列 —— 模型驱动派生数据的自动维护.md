---
title: I5：AI 列 —— 模型驱动派生数据的自动维护
outline: deep
---

# I5：AI 列 —— 模型驱动派生数据的自动维护

> Easy Data x AI 课程 · 产业应用篇 · 第 5 节

::: tip 开发状态
本节正在开发中，具体自动维护机制需要在课程采用的环境中重新验证。
:::

## 本节简介

本节讨论由模型生成的标签、摘要、向量或评分如何作为派生数据被持续维护。课程重点是数据更新机制和工程约束，而不是把一次模型调用包装成数据库自动化。

## 计划内容

- 模型驱动派生数据的定义与典型场景
- 首次回填、同步或异步更新、失败重试和幂等性
- 模型版本、提示词和数据来源的可追溯性
- 成本、延迟、质量与人工复核边界

## 与现有课程的关系

D3 关注 Agentic RAG 链路，本节进一步讨论检索所依赖的模型派生数据如何生成和维护。

## 参考资料

- [AI Native 数据库开源实现参考](https://github.com/oceanbase/seekdb)
- [OceanBase Database AI 语义搜索](https://www.oceanbase.com/docs/common-oceanbase-database-ai-1000000006779053)

## 共建说明

共建时需要用公开环境验证具体实现；在此之前，先讨论通用设计问题和可验收的实验目标，详见共建 Issue [#94](https://github.com/datawhalechina/easy-data-x-ai/issues/94)。
