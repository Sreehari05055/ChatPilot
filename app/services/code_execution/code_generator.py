# code_generator.py
from app.core.config import Config
from app import logger
class CodeGenerator:
    def __init__(self, llm_engine):
        self.llm_engine = llm_engine
    
    async def generate_code(self, task: str, metadata: dict, previous_code: str = None, previous_error: str = None) -> dict:
        """Makes LLM call to generate Python code."""
        # System prompt with metadata
        # LLM call
        # Returns {'code': '...', 'explanation': '...'}
        system_prompt = """
            You are a Python code generator that creates data analysis and machine learning code.

            Below is the file metadata, including:
            - File names
            - Sheet names
            - Columns + dtypes
            - Random samples

            {metadata}

            ==============================================================
            RULES (FOLLOW EXACTLY)
            ==============================================================

            1. **Column Name Normalization**
            - Convert all column names and all user-requested variables to **lowercase**.

            2. **Allowed Libraries**
            - USE ONLY: pandas, numpy, scikit-learn, statsmodels, matplotlib, seaborn.
            - STRICTLY FORBIDDEN: tensorflow, keras, pytorch, torch. (Do not use Deep Learning).

            3. **Output Format**
            - Always End with print() to show results
            - If you are generating code: Return ONLY executable Python code as a string.
            
            ==============================================================
            MACHINE LEARNING WORKFLOW
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
            - For numerical features: SimpleImputer + StandardScaler
            - For categorical features: SimpleImputer + OneHotEncoder
            - Combine preprocessing + model into ONE pipeline

            **STEP 3: Train-Test Split**
            - Use train_test_split (test_size=0.2, random_state=42)
            - Print shapes of train/test sets

            **STEP 4: Model Training**
            - Fit the complete pipeline on training data
            - NEVER fit preprocessing separately from the model

            **STEP 5: Evaluation**
            - Make predictions on test set
            - Print appropriate metrics (accuracy, classification_report, confusion_matrix, R2, MAE, etc.)
            - For classification: print confusion matrix and classification report
            - For regression: print MAE, RMSE, R2 score

            **STEP 6: Save Pipeline**
            - Use joblib.dump() to save the COMPLETE pipeline (not just the model)
            - Print confirmation message with filename

            ==============================================================
            TASK
            ==============================================================

            If the request is clear, generate clean, correct, production-ready Python code.
            """.format(metadata=metadata)
        
        messages = [{"role": "user", "content": task}]

        if previous_error and previous_code:
            # Add previous attempt to conversation
            messages.append({"role": "assistant", "content": previous_code})
            messages.append({"role": "user", "content": f"ERROR:\n{previous_error}\n\nFix the code."})
        
        response = await self.llm_engine._gpt_engine_stream(messages=messages, system_prompt=system_prompt, model=Config.MODEL_NAME, top_p=Config.TOP_P, max_completion_tokens=Config.MAX_TOKENS, temperature=Config.TEMPERATURE, stream=False)
        logger.info(f"generated code: {response}")
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content or ""

        return ""