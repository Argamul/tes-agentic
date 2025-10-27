import os
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.schema import HumanMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

# ---------------- Skill & Memory Data Classes ----------------
@dataclass
class SkillRecord:
    topic: str
    mastery: float = 0.0  # 0–100
    practice_count: int = 0
    last_updated: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass
class ConversationMemoryEntry:
    role: str
    text: str
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentService:
  
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model_name="gpt-3.5-turbo"
        )
        self.agents = {}
        self.tool_registry = None  # Will be injected from main app

        # tambahan untuk fitur baru
        self.skills: Dict[str, Dict[str, SkillRecord]] = {}
        self.extended_memory: Dict[str, List[ConversationMemoryEntry]] = {}

    def set_tool_registry(self, tool_registry):
        self.tool_registry = tool_registry


    async def execute(self, query: str, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if not self.tool_registry:
                raise Exception("Tool registry not initialized")

            available_tools = self.tool_registry.get_tools()
            if tools:
                selected_tools = [tool for tool in available_tools if tool.name in tools]
                if not selected_tools:
                    raise Exception(f"No valid tools found from requested list: {tools}")
            else:
                selected_tools = available_tools

            agent = initialize_agent(
                tools=selected_tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True
            )

            result = await agent.arun(query)
            return {
                "result": result,
                "tools_used": [tool.name for tool in selected_tools],
                "query": query
            }

        except Exception as e:
            logger.error(f"Error executing agent: {str(e)}")
            raise Exception(f"Agent execution failed: {str(e)}")

    async def execute_with_memory(self, query: str, conversation_id: str, tools: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if not self.tool_registry:
                raise Exception("Tool registry not initialized")

            if conversation_id not in self.agents:
                self.agents[conversation_id] = {
                    "memory": [],
                    "agent": None
                }

            available_tools = self.tool_registry.get_tools()
            if tools:
                selected_tools = [tool for tool in available_tools if tool.name in tools]
                if not selected_tools:
                    raise Exception(f"No valid tools found from requested list: {tools}")
            else:
                selected_tools = available_tools

            if not self.agents[conversation_id]["agent"]:
                self.agents[conversation_id]["agent"] = initialize_agent(
                    tools=selected_tools,
                    llm=self.llm,
                    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
                    verbose=True,
                    handle_parsing_errors=True
                )

            self.agents[conversation_id]["memory"].append({
                "query": query,
                "timestamp": asyncio.get_event_loop().time()
            })

            agent = self.agents[conversation_id]["agent"]
            result = await agent.arun(query)

            return {
                "result": result,
                "conversation_id": conversation_id,
                "memory_length": len(self.agents[conversation_id]["memory"]),
                "tools_used": [tool.name for tool in selected_tools]
            }

        except Exception as e:
            logger.error(f"Error executing agent with memory: {str(e)}")
            raise Exception(f"Agent execution with memory failed: {str(e)}")

    async def execute_chain(self, queries: List[str], tools: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        try:
            results = []
            for i, query in enumerate(queries):
                result = await self.execute(query, tools)
                result["chain_position"] = i + 1
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"Error executing agent chain: {str(e)}")
            raise Exception(f"Agent chain execution failed: {str(e)}")

    async def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        try:
            if conversation_id not in self.agents:
                return []
            return self.agents[conversation_id]["memory"]
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            raise Exception(f"Failed to get conversation history: {str(e)}")

    async def clear_conversation(self, conversation_id: str) -> bool:
        try:
            if conversation_id in self.agents:
                del self.agents[conversation_id]
                logger.info(f"Cleared conversation: {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            raise Exception(f"Failed to clear conversation: {str(e)}")

    async def get_active_conversations(self) -> List[str]:
        try:
            return list(self.agents.keys())
        except Exception as e:
            logger.error(f"Error getting active conversations: {str(e)}")
            raise Exception(f"Failed to get active conversations: {str(e)}")

    async def validate_tools(self, tools: List[str]) -> Dict[str, bool]:
        try:
            if not self.tool_registry:
                return {tool: False for tool in tools}
            available_tools = [tool.name for tool in self.tool_registry.get_tools()]
            return {tool: tool in available_tools for tool in tools}
        except Exception as e:
            logger.error(f"Error validating tools: {str(e)}")
            raise Exception(f"Tool validation failed: {str(e)}")

    # ---- Skill tracking ----
    def get_skill(self, conversation_id: str, topic: str) -> SkillRecord:
        if conversation_id not in self.skills:
            self.skills[conversation_id] = {}
        if topic not in self.skills[conversation_id]:
            self.skills[conversation_id][topic] = SkillRecord(topic=topic)
        return self.skills[conversation_id][topic]

    def update_skill(self, conversation_id: str, topic: str, delta_mastery: float):
        rec = self.get_skill(conversation_id, topic)
        rec.mastery = max(0, min(100, rec.mastery + delta_mastery))
        rec.practice_count += 1
        rec.last_updated = datetime.utcnow().timestamp()
        return rec

    # ---- Extended memory ----
    def add_to_memory(self, conversation_id: str, role: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        if conversation_id not in self.extended_memory:
            self.extended_memory[conversation_id] = []
        self.extended_memory[conversation_id].append(
            ConversationMemoryEntry(role=role, text=text, metadata=metadata or {})
        )

    # ---- Clarification ----
    async def detect_intent(self, query: str) -> Dict[str, Any]:
        lowered = query.lower()
        if any(w in lowered for w in ["latihan", "soal"]):
            return {"intent": "practice", "ambiguous": False}
        if any(w in lowered for w in ["materi", "pelajaran", "ajar"]):
            return {"intent": "lesson", "ambiguous": False}
        if len(query.split()) < 2:
            return {"intent": "unknown", "ambiguous": True, "clarify": "Bisa jelaskan lebih detail maksud Anda?"}
        return {"intent": "ask", "ambiguous": False}

    # ---- Decision layer ----
    async def execute_with_decision(self, query: str, conversation_id: str) -> Dict[str, Any]:
        self.add_to_memory(conversation_id, "user", query)
        intent_info = await self.detect_intent(query)

        if intent_info.get("ambiguous"):
            clar = intent_info.get("clarify")
            self.add_to_memory(conversation_id, "agent", clar, {"type": "clarify"})
            return {"status": "clarify", "question": clar}

        intent = intent_info["intent"]
        if intent == "lesson":
            response = f"Berikut materi untuk topik terkait: {query}"
            self.add_to_memory(conversation_id, "agent", response, {"type": "lesson"})
            return {"status": "lesson", "content": response}

        if intent == "practice":
            response = [f"Soal latihan {i+1} terkait {query}" for i in range(3)]
            self.add_to_memory(conversation_id, "agent", str(response), {"type": "practice"})
            return {"status": "practice", "questions": response}

        # fallback ke agent bawaan
        result = await self.execute_with_memory(query, conversation_id)
        return {"status": "agent", "result": result}

    # ---- Conversation loop ----
    async def conversation_loop(self, conversation_id: str = "default"):
        print("=== Mulai percakapan dengan Agent AI (ketik 'exit' untuk berhenti) ===")
        while True:
            query = input("User: ")
            if query.lower() in ["exit", "quit"]:
                print("Percakapan selesai.")
                break
            result = await self.execute_with_decision(query, conversation_id)
            if result["status"] == "clarify":
                print(f"Agent (clarify): {result['question']}")
            elif result["status"] == "lesson":
                print(f"Agent (lesson): {result['content']}")
            elif result["status"] == "practice":
                print("Agent (practice):")
                for q in result["questions"]:
                    print("-", q)
            elif result["status"] == "agent":
                print(f"Agent: {result['result']['result']}")
            else:
                print("Agent: (no response)")

