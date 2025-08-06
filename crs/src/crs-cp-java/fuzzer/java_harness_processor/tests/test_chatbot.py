import unittest
from harness.llm import ChatBot

        
class ChatBotTest(unittest.TestCase):
    def test_chatbot(self):
        ChatBot.BASE_URL = "dummy"
        ChatBot.API_KEY = "dummy"
        
        mock_response = 'What???'
        
        chatbot = ChatBot()
        chatbot.config['mock_response'] = mock_response
        chatbot.add_bot_message("Hello")
        
        res = chatbot.run()
        
        self.assertEqual(res, ['What???'])

        