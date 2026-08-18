"""X4 海量 AI Agent 多模数据降本:数据湖库登场。

分层:
  - core/*    纯 Python 标准库,可单测、可进 CI,无需 Spark 集群。
  - spark_jobs/*  运行在 docker-compose 编排的 Spark 集群内(主链路)。
  - tests/*    纯 Python 单元测试,不依赖集群/容器。
"""