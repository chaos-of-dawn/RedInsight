@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo    RedInsight - Starting...
echo ========================================
echo.

:: 获取脚本所在目录
set "PROJECT_DIR=%~dp0"
cd /d "!PROJECT_DIR!"

:: 检查关键文件
if not exist "streamlit_app.py" (
    echo [ERROR] streamlit_app.py not found
    pause
    exit /b 1
)

:: 检查Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)
python --version

:: 检查/创建虚拟环境
echo.
echo [2/4] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

:: 激活虚拟环境（模仿诊断脚本的方式）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Activation failed, trying to repair...
        python -m venv --upgrade venv >nul 2>&1
        call venv\Scripts\activate.bat >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Cannot activate virtual environment
            pause
            exit /b 1
        )
    )
) else (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

:: 检查/安装依赖（完全模仿诊断脚本的结构）
echo.
echo [3/4] Checking dependencies...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat >nul 2>&1
    python -c "import streamlit" 2>nul
    if errorlevel 1 (
        echo [INFO] Streamlit not installed, installing dependencies...
        echo [INFO] This may take 5-10 minutes...
        echo.
        
        echo [1/7] Upgrading pip...
        python -m pip install --upgrade pip >nul 2>&1
        
        echo [2/7] Installing PyTorch...
        python -m pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Failed to install PyTorch
            pause
            exit /b 1
        )
        
        python -m pip install torchvision==0.16.0+cpu --index-url https://download.pytorch.org/whl/cpu >nul 2>&1
        
        echo [3/7] Installing tokenizers...
        python -m pip install tokenizers==0.13.2 >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Failed to install tokenizers
            pause
            exit /b 1
        )
        
        echo [4/7] Installing huggingface-hub...
        python -m pip install huggingface-hub==0.11.1 >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Failed to install huggingface-hub
            pause
            exit /b 1
        )
        
        echo [5/7] Installing transformers...
        python -m pip install transformers==4.21.0 >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Failed to install transformers
            pause
            exit /b 1
        )
        
        echo [6/7] Installing sentence-transformers...
        python -m pip install sentence-transformers==2.2.2 >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Failed to install sentence-transformers
            pause
            exit /b 1
        )
        
        echo [7/7] Installing other dependencies...
        if exist "requirements.txt" (
            python -m pip install -r requirements.txt >nul 2>&1
        ) else (
            python -m pip install streamlit==1.28.2 >nul 2>&1
            if errorlevel 1 (
                echo [ERROR] Failed to install streamlit
                pause
                exit /b 1
            )
        )
        
        echo [INFO] Verifying...
        call venv\Scripts\activate.bat >nul 2>&1
        python -c "import streamlit" 2>nul
        if errorlevel 1 (
            echo [ERROR] Installation verification failed
            pause
            exit /b 1
        )
        echo [OK] Dependencies installed
    ) else (
        echo [OK] Streamlit is installed
    )
) else (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

:: 创建api_keys.json
if not exist "api_keys.json" (
    echo {} > api_keys.json
)

:: 激活检查
echo.
echo [4/4] Checking activation...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat >nul 2>&1
    if not exist "activation.json" (
        echo [WARN] Not activated yet
        echo.
        echo ========================================
        echo    Activation Required
        echo ========================================
        echo.
        echo Please complete activation to continue.
        echo.
        echo Press any key to start activation, or close this window to cancel...
        pause >nul
        echo.
        echo Starting activation...
        python activation.py
        if errorlevel 1 (
            echo.
            echo [ERROR] Activation failed or cancelled
            echo Please complete activation and try again
            pause
            exit /b 1
        )
        echo.
        echo [OK] Activation completed, continuing...
        echo.
    )
    
    :: 验证激活状态
    call venv\Scripts\activate.bat >nul 2>&1
    if exist "verify_activation.py" (
        python verify_activation.py 2>nul
    ) else (
        python check_activation.py 2>nul
    )
    if errorlevel 1 (
        echo [WARN] Activation verification failed
        echo.
        echo Possible reasons:
        echo   1. Activation file is corrupted
        echo   2. Machine code has changed
        echo   3. Activation has expired
        echo.
        echo Please run activation again: python activation.py
        pause
        exit /b 1
    )
    echo [OK] Activation verified
) else (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

:: 启动应用
echo.
echo ========================================
echo    Starting RedInsight...
echo ========================================
echo.
echo URL: http://localhost:8501
echo Press Ctrl+C to stop
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat >nul 2>&1
    cd /d "!PROJECT_DIR!"
    python -m streamlit run streamlit_app.py --server.headless=false --server.port=8501
) else (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

echo.
echo [OK] Application stopped
pause
