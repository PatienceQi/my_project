import requests

# 测试后端服务是否正确返回答案
def test_backend_response():
    url = 'http://127.0.0.1:5000/api/ask'
    question = '汕华管委规第一章第一条的主要内容是什么'
    payload = {'question': question}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print('后端返回的答案:', data.get('answer', '无答案返回'))
            print('完整返回数据:', data)
        else:
            print('请求失败，状态码:', response.status_code)
    except Exception as e:
        print('请求过程中发生错误:', str(e))

if __name__ == '__main__':
    test_backend_response()