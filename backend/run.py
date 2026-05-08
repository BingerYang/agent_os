import asyncio

# 在 import uvicorn 之前添加这段代码
if "_patch_asyncio" in getattr(asyncio.run, "__qualname__", ""):
    print("检测到 PyCharm Debug 模式，正在修复 asyncio.run 兼容性问题...")
    # 替换为原生的 asyncio.run
    asyncio.run = asyncio.runners.run

# 然后正常导入 uvicorn 并运行
import uvicorn

if __name__ == "__main__":
    # 本地开发：单体模式（管理端 + 运行时合一）
    # 生产分离部署：
    #   管理端 → uvicorn src.main_management:app --port 8000
    #   运行时 → uvicorn src.main_runtime:app --port 8001
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)  # type: ignore
