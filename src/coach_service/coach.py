"""
Main coaching service that coordinates AI providers and agents.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..ai_providers import AIProvider, Message, get_provider
from .agent_loader import AgentLoader
from .tools import ToolExecutor

logger = logging.getLogger(__name__)


class CoachService:
    """
    Main coaching service that coordinates between AI providers and coaching agents.
    """

    def __init__(
        self,
        ai_provider: AIProvider = None,
        agents_dir: str = None,
        data_dir: str = None
    ):
        """
        Initialize the coaching service.

        Args:
            ai_provider: AI provider instance (if None, uses default from env)
            agents_dir: Path to agents directory
            data_dir: Path to athlete data directory
        """
        self.provider = ai_provider or get_provider()
        self.agent_loader = AgentLoader(agents_dir)

        if data_dir is None:
            # Default to data/ relative to project root
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / 'data'
        else:
            project_root = Path(data_dir).parent

        self.data_dir = Path(data_dir)
        self.tool_executor = ToolExecutor(project_root)

    def _load_athlete_context(self) -> str:
        """
        Load athlete context files into a formatted string.

        Returns:
            Formatted string with all athlete context
        """
        context_files = [
            'athlete/goals.md',
            'athlete/training_history.md',
            'athlete/training_preferences.md',
            'athlete/upcoming_races.md',
            'athlete/current_training_status.md',
            'athlete/communication_preferences.md',
            'athlete/health_profile.md',
        ]

        context_parts = []

        for file_path in context_files:
            full_path = self.data_dir / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                    context_parts.append(f"## {file_path}\n\n{content}\n")

        return "\n".join(context_parts)

    def _load_health_data_summary(self) -> str:
        """
        Load and format recent health data summary.

        Returns:
            Formatted health data summary
        """
        health_cache = self.data_dir / 'health' / 'health_data_cache.json'

        if not health_cache.exists():
            return "No health data available."

        with open(health_cache, 'r') as f:
            data = json.load(f)

        summary_parts = []

        # Recent activities
        activities = data.get('activities', [])[:5]
        if activities:
            summary_parts.append("### Recent Activities")
            for act in activities:
                act_type = act.get('activity_type', 'Unknown')
                date = act.get('date', '')[:10]
                distance = act.get('distance_miles', 0)
                duration = act.get('duration_seconds', 0) / 60  # Convert seconds to minutes
                avg_hr = act.get('avg_heart_rate', 'N/A')
                summary_parts.append(
                    f"- {date}: {act_type}, {distance:.1f} mi, "
                    f"{duration:.0f} min, Avg HR: {avg_hr}"
                )

        # Recent RHR
        rhr_readings = data.get('resting_hr_readings', [])[:7]
        if rhr_readings:
            avg_rhr = sum(r[1] for r in rhr_readings) / len(rhr_readings)
            summary_parts.append(f"\n### Resting Heart Rate (7-day avg)")
            summary_parts.append(f"- {avg_rhr:.1f} bpm")

        # Recent sleep
        sleep_sessions = data.get('sleep_sessions', [])[:3]
        if sleep_sessions:
            summary_parts.append(f"\n### Recent Sleep")
            for sleep in sleep_sessions:
                date = sleep.get('calendar_date', '')
                hours = sleep.get('total_duration_minutes', 0) / 60
                score = sleep.get('sleep_score', 'N/A')
                summary_parts.append(f"- {date}: {hours:.1f} hrs, Score: {score}")

        # VO2 Max
        vo2_readings = data.get('vo2_max_readings', [])
        if vo2_readings:
            latest_vo2 = vo2_readings[0]
            summary_parts.append(f"\n### VO2 Max")
            vo2_value = latest_vo2.get('vo2_max', 'N/A')
            vo2_date = latest_vo2.get('date', '')[:10]
            summary_parts.append(f"- {vo2_value} ml/kg/min ({vo2_date})")

        return "\n".join(summary_parts) if summary_parts else "No health data available."

    def _select_agent(self, query: str, agent_name: str = None) -> str:
        """
        Select appropriate agent based on query or explicit agent name.

        Args:
            query: User's query
            agent_name: Optional explicit agent name

        Returns:
            Agent name to use
        """
        if agent_name:
            # Validate agent exists
            if agent_name in self.agent_loader.agents:
                return agent_name
            else:
                # Try to find close match
                for name in self.agent_loader.agents:
                    if agent_name.lower() in name.lower() or name.lower() in agent_name.lower():
                        return name
                raise ValueError(f"Unknown agent: {agent_name}")

        # Auto-detect based on query keywords
        query_lower = query.lower()

        if any(word in query_lower for word in ['run', 'pace', 'threshold', 'interval', 'marathon', 'vdot']):
            return 'running-coach'
        elif any(word in query_lower for word in ['strength', 'lift', 'squat', 'deadlift', 'gym']):
            return 'strength-coach'
        elif any(word in query_lower for word in ['mobility', 'stretch', 'flexibility', 'foam roll']):
            return 'mobility-coach'
        elif any(word in query_lower for word in ['nutrition', 'diet', 'fuel', 'eat', 'meal']):
            return 'nutrition-coach'
        else:
            # Default to running coach
            return 'running-coach'

    def chat(
        self,
        query: str,
        agent_name: str = None,
        conversation_history: List[Dict[str, str]] = None,
        include_context: bool = True
    ) -> str:
        """
        Send a coaching query and get a response.

        Args:
            query: User's question or request
            agent_name: Optional specific agent to use
            conversation_history: Optional conversation history
            include_context: Whether to include athlete context (default: True)

        Returns:
            Coach's response
        """
        # Select agent
        selected_agent = self._select_agent(query, agent_name)
        agent_config = self.agent_loader.get_agent(selected_agent)

        # Build messages
        messages = []

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                messages.append(Message(
                    role=msg.get('role', 'user'),
                    content=msg.get('content', '')
                ))

        # Add context to the user query if requested
        if include_context:
            context = self._load_athlete_context()
            health_summary = self._load_health_data_summary()

            enhanced_query = f"""
{query}

---

**ATHLETE CONTEXT:**

{context}

---

**RECENT HEALTH DATA:**

{health_summary}
"""
        else:
            enhanced_query = query

        # Add current query
        messages.append(Message(role='user', content=enhanced_query))

        # Get tool schemas
        tool_schemas = self.tool_executor.get_tool_schemas()

        # Tool calling loop - allow up to 20 tool calls
        # (agent may need: get_current_date, sync_health_data, list_recent_activities,
        # read multiple athlete files (goals, training_history, training_preferences,
        # upcoming_races, current_training_status, communication_preferences),
        # search workout library, then respond)
        max_iterations = 20
        for iteration in range(max_iterations):
            logger.info(f"Tool calling iteration {iteration + 1}/{max_iterations}")

            # Get response from AI provider with tools
            response = self.provider.chat(
                messages=messages,
                agent_config=agent_config,
                tools=tool_schemas if tool_schemas else None
            )

            # Check if this is a Gemini response object with function calls
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                # Check for function calls
                if hasattr(candidate.content, 'parts'):
                    has_function_call = False
                    text_response = ""

                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            has_function_call = True
                            # Execute the function call
                            func_call = part.function_call
                            tool_name = func_call.name
                            tool_args = dict(func_call.args)

                            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                            # Execute tool
                            tool_result = self.tool_executor.execute_tool(tool_name, tool_args)

                            logger.info(f"Tool {tool_name} result: success={tool_result.get('success', False)}")

                            # Add function result to messages for next iteration
                            messages.append(Message(
                                role='assistant',
                                content=f"[Called tool: {tool_name} with args: {tool_args}]"
                            ))
                            messages.append(Message(
                                role='user',
                                content=f"Tool result: {json.dumps(tool_result)}"
                            ))
                        elif hasattr(part, 'text') and part.text:
                            text_response += part.text

                    # If no function call, return the text response
                    if not has_function_call:
                        return text_response if text_response else "No response generated."

                    # Continue loop for next iteration with tool result
                    continue

            # If response is a string (old behavior), return it
            if isinstance(response, str):
                return response

            # If we got here with a response object but no function call, extract text
            if hasattr(response, 'text'):
                return response.text

            # Fallback
            return str(response)

        # If we exhausted iterations, log and return helpful message
        logger.warning(f"Tool calling limit ({max_iterations}) reached for query: {query[:100]}")
        return "I apologize, but I'm having trouble completing this request. The system made too many tool calls. Please try asking your question in a simpler way, or contact support if this issue persists."

    def stream_chat(
        self,
        query: str,
        agent_name: str = None,
        conversation_history: List[Dict[str, str]] = None,
        include_context: bool = True
    ):
        """
        Stream a coaching response.

        Args:
            query: User's question or request
            agent_name: Optional specific agent to use
            conversation_history: Optional conversation history
            include_context: Whether to include athlete context (default: True)

        Yields:
            Chunks of the response
        """
        # Select agent
        selected_agent = self._select_agent(query, agent_name)
        agent_config = self.agent_loader.get_agent(selected_agent)

        # Build messages
        messages = []

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                messages.append(Message(
                    role=msg.get('role', 'user'),
                    content=msg.get('content', '')
                ))

        # Add context to the user query if requested
        if include_context:
            context = self._load_athlete_context()
            health_summary = self._load_health_data_summary()

            enhanced_query = f"""
{query}

---

**ATHLETE CONTEXT:**

{context}

---

**RECENT HEALTH DATA:**

{health_summary}
"""
        else:
            enhanced_query = query

        # Add current query
        messages.append(Message(role='user', content=enhanced_query))

        # Stream response from AI provider
        for chunk in self.provider.stream_chat(
            messages=messages,
            agent_config=agent_config
        ):
            yield chunk

    def list_agents(self) -> Dict[str, str]:
        """Get list of available agents with descriptions."""
        return self.agent_loader.get_agent_info()
