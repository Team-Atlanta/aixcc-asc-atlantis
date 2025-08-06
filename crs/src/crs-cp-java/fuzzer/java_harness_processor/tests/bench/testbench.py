# multi processing pool
from multiprocessing import Pool, current_process
import time

class TestBench:
    def __init__(self):
        pass
    
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
    
    def batch(self):
        pass
    
    def _bench_init(self):
        if not hasattr(self, 'name'):
            self.name =  f'{self.__class__.__name__}-{str(current_process().pid)}'
        
    def _bench_loop(self):
        self._bench_init()
        return self.batch() 
    
    def bench(self, n=5):
        self.setUp()
        if n == 1:
            results = [self._bench_loop()]
        else :
            with Pool(n) as pool:
                results = pool.starmap(self._bench_loop, [() for _ in range(n)])
        self.tearDown()
        return results

# Example usage
'''
class MyTest(TestBench):
    def batch(self):
        print(10)
        return 1
    
if __name__ == "__main__":
    mytest = MyTest()
    res = mytest.bench(20)
    print(res)
'''