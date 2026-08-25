---
title: I3：SQL × AI —— AI Functions 的设计与执行
outline: deep
---

# I3：SQL × AI —— AI Functions 的设计与执行

> Easy Data x AI 课程 · 产业应用篇 · 第 3 节

::: tip 开发状态
本节正在开发中，具体接口和示例需要在课程采用的环境中重新验证。
:::

## 本节简介

本节讨论如何把 Embedding、生成和重排等模型能力放进 SQL 数据处理链路。重点不是记住函数名称，而是理解数据库如何组织模型调用、数据流、失败处理和结果落库。

## 计划内容

- SQL 与模型调用结合的典型方式
- Embedding、生成、提示词和重排函数
- 模型端点、批处理、超时、重试和成本控制
- 权限、隐私、可观测性与结果可重复性

## 与现有课程的关系

本节在 D2 的数据层基础上继续讨论 SQL 内 AI 能力的设计与执行，具体实验以公开、可运行的课程环境为准。

## 参考资料

- [AI Native 数据库开源实现参考](https://github.com/oceanbase/seekdb)
- [AI 函数服务语法及示例](https://www.oceanbase.com/docs/common-oceanbase-database-cn-1000000004476158)

## 共建说明

本节需要结合可公开、可运行的环境补齐实验，相关接口和步骤应在合入前重新验证，详见共建 Issue [#92](https://github.com/datawhalechina/easy-data-x-ai/issues/92)。
