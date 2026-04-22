from fastapi.templating import Jinja2Templates
from fastapi import Request

# 模拟 Request 对象
class MockRequest:
    def __init__(self):
        self.scope = {"type": "http"}
        self.headers = {}
        self.method = "GET"

# 初始化模板
templates = Jinja2Templates(directory='templates')

# 测试模板渲染
try:
    request = MockRequest()
    context = {'request': request}
    response = templates.TemplateResponse('index.html', context)
    print("模板渲染成功！")
except Exception as e:
    print(f"模板渲染失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
