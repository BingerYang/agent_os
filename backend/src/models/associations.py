from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Table
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

pipeline_sub_agents = Table(
    "pipeline_sub_agents",
    Base.metadata,
    Column("pipeline_id", BigInteger, ForeignKey("pipelines.id", ondelete="CASCADE"), primary_key=True),
    Column("agent_id", BigInteger, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("order_index", Integer, default=0),
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
