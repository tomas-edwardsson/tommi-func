from modules import func_module

class Test(func_module.FuncModule):
    version = "11.11.11"
    api_version = "0.0.1"
    description = "Just a very simple example module"
    def __init__(self):
        self.methods = {
            "add":  self.add,
            "ping": self.ping,
            "sleep": self.sleep
        }
        func_module.FuncModule.__init__(self)

    def add(self, numb1, numb2):
        return numb1 + numb2

    def ping(self):
        return 1

    def sleep(t):
        """
        Sleeps for t seconds, and returns time of day.
        Simply a test function for trying out async and threaded voodoo.
        """
        t = int(t)
        time.sleep(t)
        return time.time()

methods = Test()
register_rpc = methods.register_rpc
