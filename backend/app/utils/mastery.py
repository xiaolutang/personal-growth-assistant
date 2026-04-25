"""掌握度计算工具模块

统一掌握度阈值式算法，消除 review_service 与 knowledge_service 之间的循环依赖。

规则：
- relationship_count 折算为等价 entry_count（每 2 个关系 ≈ 1 个条目）
- effective_count = entry_count + relationship_count // 2
- effective_count >= 6 且 note_ratio > 0.3 → advanced
- effective_count >= 3 且 recent_count > 0 → intermediate
- effective_count >= 1 → beginner
- 其他 → new
"""


def calculate_mastery_from_stats(
    entry_count: int,
    recent_count: int = 0,
    note_count: int = 0,
    relationship_count: int = 0,
) -> str:
    """根据统计数据计算掌握度（阈值式算法）

    Args:
        entry_count: 条目数量
        recent_count: 近期条目数量
        note_count: 笔记数量
        relationship_count: 关系数量（每 2 个关系折算为 1 个条目）

    Returns:
        掌握度标签: "new" | "beginner" | "intermediate" | "advanced"
    """
    effective_count = entry_count + max(0, relationship_count // 2)

    if effective_count == 0:
        return "new"

    note_ratio = note_count / effective_count if effective_count > 0 else 0

    if effective_count >= 6 and note_ratio > 0.3:
        return "advanced"
    elif effective_count >= 3 and recent_count > 0:
        return "intermediate"
    elif effective_count >= 1:
        return "beginner"
    return "new"
