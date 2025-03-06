import dotenv
from openai import OpenAI


class Chat_GPT():
    def __init__(self, chatbot_api, prompt_path):
        #ユーザー登録変数の読み込み
        dotenv.load_dotenv()
        #CAHT_GPTのオブジェクトを作成
        self.gpt_client = OpenAI(api_key=chatbot_api)
        #プロンプトを取得
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()
        #プロンプトを入力したメッセージListを作成
        self.messagelist=[{"role": "system", "content": prompt}]


    async def chatbot_response(self, message):
        """Chat-GPTにメッセージを入力してレスポンスを返す"""
        #入力メッセージを追加
        try:
            text = message.content
        except AttributeError:
            #テキストが直接渡された時
            text = message
        self.messagelist.append({"role": "user", "content": text})
        #メッセージをChatGPTに入力
        response = self.gpt_client.chat.completions.create(model = "gpt-4-turbo", messages=self.messagelist)

        #返答を取得
        response_text = response.choices[0].message.content
        #返答をメッセージListに保存
        self.messagelist.append({"role": "assistant", "content": response_text})

        if len(self.messagelist) >= 12:
            del self.messagelist[1:3]

        return response_text