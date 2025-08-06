
'''
Default: 
    Log.level = 'info' 
'''
class Log:
    level = 'info'
    
    @staticmethod
    def d(msg):
        if Log.level == 'debug':
            print(f'[DEBUG] {msg}')
            
    @staticmethod
    def i(msg):
        if Log.level in ['debug', 'info']:
            print(f'[INFO] {msg}')
            
    @staticmethod
    def w(msg):
        if Log.level in ['debug', 'info', 'warn']:
            print(f'[WARN] {msg}')
            
    @staticmethod
    def e(msg):
        if Log.level in ['debug', 'info', 'warn', 'error']:
            print(f'[ERROR] {msg}')
        