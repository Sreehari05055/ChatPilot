# code_generator.py
from app.core.config import Config
from app import logger
class CodeGenerator:
    def __init__(self, llm_engine):
        self.llm_engine = llm_engine
    
    async def generate_code(self, analysis_plan: list[str], task_type: str, metadata: dict, target_column: str | None = None, risk_checks: list[str] | None = None, previous_code: str = None, previous_error: str = None) -> str:
        """Makes LLM call to generate Python code."""
        # System prompt with metadata
        # LLM call
        # Returns code as string
        system_prompt = f"""
        You are a Python code generator that creates data analysis and machine learning code.

        Below is the file metadata, including:
        - File names
        - Sheet names
        - Columns + dtypes

        {metadata}

        ==========
        CRITICAL INSTRUCTIONS
        ==========
        - You must use the exact file names when loading data
        - Filenames: {'\n'.join(metadata.keys())} 

        ==============================================================
        TASK CONTEXT (STRUCTURED — FOLLOW EXACTLY)
        ==============================================================

        You are given:
        - analysis_plan: an ordered list of concrete steps to execute
        - task_type: the category of the task
        - target_column: the target variable (only for ML tasks, may be null)
        - risk_checks: data quality or leakage checks to run (may be empty)

        You MUST follow the analysis_plan in order.

        IMPORTANT BEHAVIOR RULE:
        - If task_type starts with "ml_", you MUST follow the MACHINE LEARNING WORKFLOW.
        - If task_type does NOT start with "ml_", you MUST NOT apply the MACHINE LEARNING WORKFLOW.

        ==============================================================
        RULES (FOLLOW EXACTLY)
        ==============================================================

        1. **Column Name Normalization**
        - Convert all column names and all user-requested variables to **lowercase**.

        2 **Always configure stdout and stderr to handle Unicode**
        - Use the following code at the start of your script:
        ```python 
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        ```
        3. **Allowed Libraries**
        - USE ONLY: pandas, numpy, scikit-learn, statsmodels, matplotlib, seaborn.
        - STRICTLY FORBIDDEN: tensorflow, keras, pytorch, torch.

        4. **Output Format**
        - CRITICAL: You MUST print() ALL results, findings, and outputs
        - Every analysis step MUST have print() statements showing the results
        - Use print() for dataframes (df.head()), statistics, plots saved messages, etc.
        - Return ONLY executable Python code as a string
        - Do NOT include explanations, comments, or markdown
        - If no results are printed, the analysis is INCOMPLETE

        ==============================================================
        MACHINE LEARNING WORKFLOW (APPLY ONLY IF task_type STARTS WITH "ml_")
        ==============================================================

        When building ML models, ALWAYS follow this sequence:

        **STEP 1: Exploratory Data Analysis (EDA)**
        - Load data and check shape, dtypes, missing values
        - Print summary statistics (df.describe())
        - Check class distribution for classification tasks
        - Identify numerical vs categorical columns
        - Print correlation matrix for numerical features

        **STEP 2: Data Preprocessing Pipeline**
        - Use scikit-learn Pipeline and ColumnTransformer
        - Numerical: SimpleImputer + StandardScaler
        - Categorical: SimpleImputer + OneHotEncoder
        - Combine preprocessing + model into ONE pipeline

        **STEP 3: Train-Test Split**
        - train_test_split (test_size=0.2, random_state=42)
        - Print shapes

        **STEP 4: Model Training**
        - Fit the complete pipeline on training data

        **STEP 5: Evaluation**
        - Classification: confusion matrix + classification_report
        - Regression: MAE, RMSE, R2

        **STEP 6: Save Pipeline**
        - joblib.dump() the COMPLETE pipeline
        - Print confirmation

        ==============================================================
        EXECUTION INSTRUCTIONS
        ==============================================================

        - Implement each step from analysis_plan explicitly
        - Run any listed risk_checks (e.g., leakage, missing targets)
        - Keep code minimal and deterministic
        - If previous_code and previous_error are provided, FIX the error without changing the intent
        """
        

        # Build user task message
        analysis_plan_str = "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(analysis_plan)
        )

        task_context = f"""
            analysis_plan (execute in order):
            {analysis_plan_str}

            task_type:
            {task_type}

            target_column:
            {target_column}

            risk_checks:
            {", ".join(risk_checks) if risk_checks else "none"}
        """

        messages = [{"role": "user", "content": task_context}]

        if previous_error and previous_code:
            # Add previous attempt to conversation
            messages.append({"role": "assistant", "content": previous_code})
            messages.append({"role": "user", "content": f"ERROR:\n{previous_error}\n\nFix the code."})
        
        # Use higher token limit for code generation
        code_gen_max_tokens = max(Config.MAX_TOKENS, 4000)
        
        response = await self.llm_engine._gpt_engine_stream(messages=messages, system_prompt=system_prompt, model=Config.MODEL_NAME, top_p=Config.TOP_P, max_completion_tokens=code_gen_max_tokens, temperature=Config.TEMPERATURE, stream=False, use_tools=False)
        logger.info(f"generated code: {response}")
        
        # Handle OpenAI format
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content or ""
        
        # Handle Anthropic format
        if hasattr(response, "content") and response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
        
        return ""