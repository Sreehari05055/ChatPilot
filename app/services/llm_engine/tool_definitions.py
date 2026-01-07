"""Unified tool definitions for all LLM providers.

OpenAI/DeepSeek use 'tools' format, Anthropic uses 'functions' format.
Define once here and import in each engine.
"""

# OpenAI/DeepSeek format
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for general knowledge, current events, or information NOT related to uploaded files. Do NOT use this for analyzing uploaded data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's question to be rephrased and web searched."
                    }
                },
                "required": ["question"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and analyze the content of a specific URL provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "format": "uri",
                        "description": "The exact URL to fetch content from."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "REQUIRED for ANY questions about uploaded CSV/Excel files. Use this to perform data analysis, statistics, visualizations, filtering, aggregations, or machine learning on uploaded data. Check the UPLOADED FILE METADATA in the system message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_plan": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Ordered, concrete analysis steps to perform. Each step must be specific and actionable."
                    },
                    "task_type": {
                        "type": "string",
                        "enum": [
                        "eda",
                        "aggregation",
                        "filtering",
                        "statistics",
                        "ml_classification",
                        "ml_regression",
                        "clustering",
                        "time_series"
                    ],
                        "description": "The type of analysis task to perform."
                    },
                    "target_column": {
                        "type": ["string", "null"],
                        "description": "Target variable for ML tasks, null otherwise."
                    },
                    "risk_checks": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Specific risk or bias checks to perform on the data or model."
                }
                },
                "required": ["analysis_plan", "task_type"]
            }
        }
    }
]

# Anthropic format (uses 'input_schema' instead of 'parameters')
ANTHROPIC_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for general knowledge, current events, or information NOT related to uploaded files. Do NOT use this for analyzing uploaded data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user's question to be rephrased and web searched."
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "web_fetch",
        "description": "Fetch and analyze the content of a specific URL provided by the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "The exact URL to fetch content from."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "analyze_data",
        "description": "REQUIRED for ANY questions about uploaded CSV/Excel files. Use this to perform data analysis, statistics, visualizations, filtering, aggregations, or machine learning on uploaded data. Check the UPLOADED FILE METADATA in the system message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "analysis_plan": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Ordered, concrete analysis steps to perform. Each step must be specific and actionable."
                },
                "task_type": {
                    "type": "string",
                    "enum": [
                        "eda",
                        "aggregation",
                        "filtering",
                        "statistics",
                        "ml_classification",
                        "ml_regression",
                        "clustering",
                        "time_series"
                    ],
                    "description": "The type of analysis task to perform."
                },
                "target_column": {
                    "type": "string",
                    "description": "Target variable for ML tasks, null otherwise."
                },
                "risk_checks": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Specific risk or bias checks to perform on the data or model."
                }
            },
            "required": ["analysis_plan", "task_type"]
        }
    }
]
