"""Golden Dataset 评估框架

提供 Agent 行为评估的核心组件：
- TestCase / NegativeTestCase: 测试用例数据类
- DatasetLoader: 从 JSON 加载测试用例
- pass_at_k / pass_hat_k: 通过率指标计算
- GoldenDatasetRunner: 评估执行器（环境隔离）
- EvaluationReport: 通过率统计报告
"""
