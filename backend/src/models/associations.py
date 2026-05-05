from sqlalchemy import BigInteger, Column, ForeignKey, Table
from src.core.database import Base

agent_tools = Table(
    "agent_tools",
    Base.metadata,
    Column("agent_id", BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("tool_id", BigInteger, ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
)

agent_skills = Table(
    "agent_skills",
    Base.metadata,
    Column("agent_id", BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", BigInteger, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

pipeline_detection_rules = Table(
    "pipeline_detection_rules",
    Base.metadata,
    Column("pipeline_id", BigInteger, ForeignKey("pipelines.id", ondelete="CASCADE"), primary_key=True),
    Column("rule_id", BigInteger, ForeignKey("detection_rules.id", ondelete="CASCADE"), primary_key=True),
)

skill_tools = Table(
    "skill_tools",
    Base.metadata,
    Column("skill_id", BigInteger, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    Column("tool_id", BigInteger, ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
)
