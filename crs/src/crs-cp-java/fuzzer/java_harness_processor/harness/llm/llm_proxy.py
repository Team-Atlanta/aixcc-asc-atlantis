import time
# import litellm
from openai import OpenAI
from ..utils.logger import Log

class Config:
    base_url            = ""
    api_key             = ""
    model               = "claude-3.5-sonnet"
    temperature         = 0
    top_p               = 1
    n                   = 1
    max_tokens          = 4096
    custom_llm_provider = "openai"

config = Config()

class OpenAI_Session:
    def __init__(self, config):
        self.config = config
    
    def request(self, messages):
        client = OpenAI( 
            api_key = self.config["api_key"], 
            base_url = self.config["base_url"]
        )
        
        config = {
            "model":        self.config["model"],
            "temperature":  self.config["temperature"],
            "top_p":        self.config["top_p"],
            "n":            self.config["n"],
            "max_tokens":   self.config["max_tokens"]
        }
        
        return client.chat.completions.create(messages = messages, **config)
    
    def close(self):
        pass

TRY_COUNT = 5
class ChatBot:
    def __init__(self, base_url             = None, 
                        api_key             = None, 
                        model               = None, 
                        temperature         = None, 
                        top_p               = None, 
                        n                   = None, 
                        max_tokens          = None, 
                        custom_llm_provider = None):
        
        self.config = {
            "base_url": base_url if base_url else config.base_url,
            "api_key": api_key if api_key else config.api_key,
            "model": model if model else config.model,
            "temperature": temperature if temperature else config.temperature,
            "top_p": top_p if top_p else config.top_p,
            "n": n if n else config.n,
            "max_tokens": max_tokens if max_tokens else config.max_tokens,
            "custom_llm_provider": custom_llm_provider if custom_llm_provider else config.custom_llm_provider
        }
        
        self._dialog = []
        self._last_responses = None
    
    
    def add_system_message(self, message):
        self._dialog.append({"role": "system", "content": message})
        
    def add_user_message(self, message):
        self._dialog.append({"role": "user", "content": message})
        
    def add_bot_message(self, message):
        self._dialog.append({"role": "assistant", "content": message})
    
    def get_dialog(self):
        return self._dialog
    
    def clear_dialog(self):
        self._dialog = []
        
    log_count = 0
    def run(self):
        session = OpenAI_Session(config=self.config)

        for i in range(TRY_COUNT):
            try:
                response = session.request(self._dialog)
                break
            except Exception as e:
                Log.e(f"LLM request retry. : {e}")
                if i == TRY_COUNT - 1:
                    raise Exception("LLM_REQUEST_FAILED")
                time.sleep(3)
            
        self._last_responses = [choice.message.content for choice in response.choices]
        
        for response_message in self._last_responses:
            self.add_bot_message(response_message)
        
        return self._last_responses
